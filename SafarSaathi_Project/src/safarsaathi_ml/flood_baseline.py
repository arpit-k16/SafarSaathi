"""CPU pixel-segmentation baseline for publisher-labelled STURM flood scenes.

The target is the publisher's binary reference-positive water/flood extent.
It must not be interpreted as calibrated temporary-flood probability.
"""
import io
import json
from datetime import datetime,timezone
from pathlib import Path
import zipfile

import joblib
import numpy as np
import pandas as pd
from scipy.ndimage import uniform_filter
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .artifacts import load_artifact
from .pipeline import sha256,utc_now
from .registry import load_registry,register_model

MODEL_ID='flood_segmentation_model'
SEED=20261025
GEO_TAGS=(33550,33922,34264,34735,34736,34737)
LIMITATIONS=['Experimental STURM reference-positive water/flood-extent segmentation, not an official flood warning.',
 'Does not independently distinguish permanent water from temporary inundation; class mapping follows publisher mask > 0.',
 'Only delivered preprocessed 128x128 two-band Sentinel-1 tiles are supported; raw local GRD/dB scenes are not interchangeable.',
 'Country/event holdout benchmark; Uttarakhand and arbitrary new sensors/normalizations have not been validated.',
 'Reference and Sentinel acquisitions may differ by up to 24 hours in the selected experiment.',
 'Model scores are not calibrated real-world flood probabilities.']


def image_features(image):
    image=np.asarray(image,dtype=np.float32)
    if image.shape!=(128,128,2) or not np.isfinite(image).all():raise ValueError('Expected finite preprocessed Sentinel-1 image of shape 128x128x2.')
    if np.abs(image).max()>10:raise ValueError('Input is outside supported delivered preprocessing range; raw GRD/dB is unsupported.')
    mean=uniform_filter(image,size=(3,3,1),mode='reflect')
    variance=np.maximum(uniform_filter(image*image,size=(3,3,1),mode='reflect')-mean*mean,0)
    return np.concatenate([image,mean,np.sqrt(variance),image[:,:,:1]-image[:,:,1:]],axis=2).reshape(-1,7)


def read_tiff_bytes(payload):
    import tifffile
    with tifffile.TiffFile(io.BytesIO(payload)) as source:
        array=source.asarray()
        tags={str(k):source.pages[0].tags[k].value for k in GEO_TAGS if k in source.pages[0].tags}
    return array,tags


def read_pair(archive,tile):
    image,tags=read_tiff_bytes(archive.read('Dataset/Sentinel1/S1/'+tile))
    mask,mask_tags=read_tiff_bytes(archive.read('Dataset/Sentinel1/Floodmaps/'+tile))
    if image.shape!=(128,128,2) or mask.shape!=(128,128):raise ValueError('Image/mask dimensions do not align.')
    if not tags or tags!=mask_tags:raise ValueError('Image/mask GeoTIFF tags do not align.')
    if not np.isfinite(mask).all() or not np.issubdtype(mask.dtype,np.integer) or mask.min()<0 or mask.max()>10:
        raise ValueError('Unexpected publisher mask encoding.')
    # Published STURM utility preprocess_mask uses all values >0 as its reference-positive class.
    binary=(mask>0).astype(np.uint8)
    return image,binary,tags,np.unique(mask).tolist()


def confusion_metrics(counts):
    tn,fp,fn,tp=[int(v) for v in counts]
    ratio=lambda n,d:float(n/d) if d else None
    return {'precision':ratio(tp,tp+fp),'recall':ratio(tp,tp+fn),'IoU':ratio(tp,tp+fp+fn),'Dice_F1':ratio(2*tp,2*tp+fp+fn),
            'non_flood_IoU':ratio(tn,tn+fp+fn),'non_flood_precision':ratio(tn,tn+fn),'non_flood_recall':ratio(tn,tn+fp),
            'confusion_matrix':[[tn,fp],[fn,tp]],'pixel_count':tn+fp+fn+tp,'reference_positive_prevalence':ratio(tp+fn,tn+fp+fn+tp)}


def evaluate_tiles(archive,rows,model,threshold):
    counts=np.zeros(4,dtype=np.int64);scenes=[]
    for row in rows.itertuples():
        image,actual,_,_=read_pair(archive,row.tile_id)
        prediction=model.predict_proba(image_features(image))[:,1].reshape(128,128)>=threshold
        a=actual.astype(bool)
        cm=np.array([np.sum(~a&~prediction),np.sum(~a&prediction),np.sum(a&~prediction),np.sum(a&prediction)])
        counts+=cm
        scenes.append({'tile':row.tile_id,'event':row.ems_code,'country':row.country,**confusion_metrics(cm)})
    return {**confusion_metrics(counts),'scenes':scenes}


def split_metadata(metadata):
    required={'tile_id','ems_code','country','epsg_code','sentinel_date','floodmap_date'}
    if not required.issubset(metadata) or metadata[list(required)].isna().any().any() or metadata.tile_id.duplicated().any():raise ValueError('Invalid event/scene metadata.')
    difference=(pd.to_datetime(metadata.floodmap_date)-pd.to_datetime(metadata.sentinel_date)).abs().dt.total_seconds()/3600
    eligible=metadata[difference<=24].copy()
    # Countries, not overlapping patches, are assigned first. Every EMS event belongs to exactly one country here.
    if metadata.groupby('ems_code').country.nunique().max()!=1:raise ValueError('Cross-country shared event requires grouped split repair.')
    countries=np.array(sorted(eligible.country.unique()));rng=np.random.default_rng(SEED);rng.shuffle(countries)
    if len(countries)<9:raise ValueError('Need at least nine eligible country groups for independent splits.')
    train_end=int(len(countries)*.6);validation_end=train_end+int(len(countries)*.2)
    groups={'train':countries[:train_end].tolist(),'validation':countries[train_end:validation_end].tolist(),'test':countries[validation_end:].tolist()}
    result={}
    for split,selected in groups.items():
        subset=eligible[eligible.country.isin(selected)]
        rows=[group.sample(n=min(6,len(group)),random_state=SEED) for _,group in subset.groupby('ems_code',sort=True)]
        result[split]=pd.concat(rows).sort_values('tile_id').reset_index(drop=True)
    for a,b in [('train','validation'),('train','test'),('validation','test')]:
        if set(result[a].ems_code)&set(result[b].ems_code) or set(result[a].country)&set(result[b].country):raise ValueError('Event/geographic leakage.')
    return result,groups,{'total_s1_tiles':len(metadata),'eligible_within_24_hours':len(eligible),'excluded_time_mismatch':len(metadata)-len(eligible)}


def train_flood(project,data):
    if any(m['model_id']==MODEL_ID for m in load_registry(project/'models/registry.json')):raise ValueError('Flood model already registered; no overwrite.')
    verified=json.loads((data/'download_verification.json').read_text(encoding='utf-8'))
    archive_path=data/'Dataset.zip'
    if not verified.get('publisher_checksum_matched') or archive_path.stat().st_size!=verified['bytes']:raise ValueError('Verified complete archive is required.')
    # Recheck SHA once on completed local archive before using any pixels.
    if sha256(archive_path)!=verified['sha256']:raise ValueError('Dataset archive checksum changed.')
    with zipfile.ZipFile(archive_path) as archive:
        metadata=pd.read_csv(archive.open('Dataset/Sentinel1_metadata.csv'))
        splits,countries,inventory=split_metadata(metadata)
        features,labels=[],[];class_values=set();validation_pairs=[]
        rng=np.random.default_rng(SEED)
        for row in splits['train'].itertuples():
            image,mask,tags,values=read_pair(archive,row.tile_id);class_values.update(values)
            x=image_features(image);sample=rng.choice(len(x),size=512,replace=False)
            features.append(x[sample]);labels.append(mask.ravel()[sample])
        x=np.concatenate(features);y=np.concatenate(labels)
        if len(np.unique(y))!=2:raise ValueError('Both observed reference classes are required.')
        candidates={'logistic':make_pipeline(StandardScaler(),LogisticRegression(class_weight='balanced',max_iter=400,random_state=SEED)),
                    'gradient_boosting':HistGradientBoostingClassifier(max_iter=80,max_leaf_nodes=15,l2_regularization=1,random_state=SEED,class_weight='balanced')}
        comparison={};best=None;best_score=-1
        for name,model in candidates.items():
            model.fit(x,y)
            comparison[name]={}
            for threshold in (.3,.5,.7):
                score=evaluate_tiles(archive,splits['validation'],model,threshold)
                comparison[name][str(threshold)]={k:v for k,v in score.items() if k!='scenes'}
                if score['IoU'] is not None and score['IoU']>best_score:
                    best=(name,model,threshold);best_score=score['IoU']
        if best is None:raise ValueError('No meaningful validation reference-positive IoU is defined.')
        name,model,threshold=best
        test=evaluate_tiles(archive,splits['test'],model,threshold)
        validation=evaluate_tiles(archive,splits['validation'],model,threshold)
        version=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');folder=project/'models/flood_segmentation'/version
        folder.mkdir(parents=True,exist_ok=False);artifact=folder/'pipeline.joblib'
        bundle={'model':model,'threshold':threshold,'method':name}
        joblib.dump(bundle,artifact);loaded=joblib.load(artifact)
        image,mask,tags,_=read_pair(archive,splits['test'].iloc[0].tile_id)
        if not np.array_equal(loaded['model'].predict_proba(image_features(image)),model.predict_proba(image_features(image))):raise ValueError('Flood artifact reload mismatch.')
        # A bounded real held-out example supports local UI tests, never packaged as a raw dataset.
        example=project/'data/interim/flood_ui_example';example.mkdir(exist_ok=True)
        payload={'image':image.tolist(),'metadata':{'source_format':'STURM-S1-preprocessed','geo_tags':{k:list(v) if isinstance(v,tuple) else v for k,v in tags.items()}}}
        (example/'image.json').write_text(json.dumps(payload,separators=(',',':')),encoding='utf-8')
        from PIL import Image
        prediction=(model.predict_proba(image_features(image))[:,1].reshape(128,128)>=threshold).astype(np.uint8)
        Image.fromarray(prediction*255).save(folder/'heldout_prediction.png')
        Image.fromarray(mask*255).save(folder/'heldout_reference.png')
    report={'validation_comparison':comparison,'selected_method':name,'threshold':threshold,'selection':'Maximum reference-positive IoU on validation countries only; test never used for choice.',
            'validation':validation,'test':test,'always_negative_baseline':{'reference_positive_IoU':0.0,'reference_positive_Dice':0.0},
            'class_mapping':{'0':'reference-negative','1':'publisher reference-positive water/flood extent (raw mask >0)'},'raw_class_values_in_training':sorted(class_values),
            'splits':{k:{'countries':countries[k],'events':sorted(v.ems_code.unique().tolist()),'tiles':v.tile_id.tolist()} for k,v in splits.items()},
            'inventory':inventory,'sampled_training_pixels':len(y),'training_reference_positive_fraction':float(y.mean())}
    entry={'model_id':MODEL_ID,'model_version':version,'task':'reference water/flood extent pixel segmentation','task_type':'image_segmentation',
           'trained_at':utc_now(),'artifact':artifact.relative_to(project).as_posix(),'artifact_sha256':sha256(artifact),'persistence_test_passed':True,
           'training_completed':True,'quality_status':'TRAINED_BUT_EXPERIMENTAL','target_definition':report['class_mapping'],
           'dataset_provenance':{'doi':'10.5281/zenodo.12748983','sha256':verified['sha256'],'publisher_md5':verified['md5'],'bytes':verified['bytes'],'license':'CC BY 4.0 (Zenodo dataset record)',
             'reference_mapping_source':'https://github.com/STURM-WEO/STURM-Flood/blob/main/utils/utility.py','scope':'Selected Sentinel-1 labelled benchmark subset; not full dataset or local Uttarakhand scenes.'},
           'feature_schema':{'image_shape':[128,128,2],'input':'Delivered STURM preprocessed float32 Sentinel-1 bands; finite values within [-10,10]',
             'features':['two bands','3x3 local band means','3x3 local band standard deviations','band difference'],'output_shape':[128,128]},
           'configuration':{'seed':SEED,'max_tiles_per_event':6,'pixels_per_training_tile':512,'country_split':[.6,.2,.2],
             'maximum_reference_time_offset_hours':24,'augmentation':'none','compute':'CPU; bounded tiles, no full archive extraction or pretrained weights'},
           'metrics':report,'limitations':LIMITATIONS}
    for filename,payload in [('metadata.json',entry),('evaluation.json',report),('feature_schema.json',entry['feature_schema'])]:
        (folder/filename).write_text(json.dumps(payload,indent=2,allow_nan=False),encoding='utf-8')
    register_model(project/'models/registry.json',entry)
    return entry


def load_flood(project):
    entry=next((m for m in load_registry(project/'models/registry.json') if m['model_id']==MODEL_ID),None)
    if entry is None:raise ValueError('No flood-scene segmentation model is registered.')
    bundle=load_artifact(project,entry)
    if not {'model','threshold'}.issubset(bundle):raise ValueError('Invalid flood model artifact.')
    return entry,bundle


def segment(project,payload):
    if not isinstance(payload,dict) or set(payload)!={'image','metadata'}:raise ValueError('Expected image and metadata only.')
    metadata=payload['metadata']
    if not isinstance(metadata,dict) or metadata.get('source_format')!='STURM-S1-preprocessed':raise ValueError('Only STURM-S1-preprocessed input is supported.')
    if set(metadata)!={'source_format','geo_tags'} or not isinstance(metadata['geo_tags'],dict) or not set(metadata['geo_tags']).issubset({str(k) for k in GEO_TAGS}):
        raise ValueError('Unsupported geospatial metadata schema.')
    if len(json.dumps(metadata))>10000:raise ValueError('Geospatial metadata exceeds limit.')
    x=image_features(payload['image']);entry,bundle=load_flood(project)
    probability=bundle['model'].predict_proba(x)[:,1].reshape(128,128)
    return {'status':'ok','model_id':MODEL_ID,'model_version':entry['model_version'],'quality_status':'TRAINED_BUT_EXPERIMENTAL',
            'mask':(probability>=bundle['threshold']).astype(int).tolist(),'confidence_map':probability.tolist(),
            'threshold':bundle['threshold'],'dimensions':[128,128],'input_metadata':metadata,'class_mapping':entry['target_definition'],
            'limitations':LIMITATIONS}


def segment_geotiff(project,input_path,output_path):
    """Explicit local CLI/library use only. HTTP clients cannot select filesystem paths."""
    import tifffile
    input_path,output_path=Path(input_path),Path(output_path)
    if input_path.stat().st_size>2_000_000:raise ValueError('Supported tile TIFF must be <=2 MB.')
    if output_path.exists():raise ValueError('Output already exists; no overwrite.')
    payload=input_path.read_bytes();image,tags=read_tiff_bytes(payload)
    result=segment(project,{'image':image,'metadata':{'source_format':'STURM-S1-preprocessed','geo_tags':{k:list(v) if isinstance(v,tuple) else v for k,v in tags.items()}}})
    with tifffile.TiffFile(io.BytesIO(payload)) as source:
        extra=[(k,source.pages[0].tags[k].dtype,source.pages[0].tags[k].count,source.pages[0].tags[k].value,False) for k in GEO_TAGS if k in source.pages[0].tags]
    tifffile.imwrite(output_path,np.asarray(result['mask'],dtype=np.uint8),photometric='minisblack',extratags=extra,metadata=None)
    _,saved_tags=read_tiff_bytes(output_path.read_bytes())
    if saved_tags!=tags:raise ValueError('Output geospatial metadata did not round-trip.')
    return {'model_id':MODEL_ID,'output_dimensions':result['dimensions'],'geospatial_metadata_preserved':True,'threshold':result['threshold'],'limitations':LIMITATIONS}


def evaluate_flood(project,data):
    entry,bundle=load_flood(project)
    with zipfile.ZipFile(Path(data)/'Dataset.zip') as archive:
        metadata=pd.read_csv(archive.open('Dataset/Sentinel1_metadata.csv'))
        ids=entry['metrics']['splits']['test']['tiles']
        rows=metadata[metadata.tile_id.isin(ids)].sort_values('tile_id').reset_index(drop=True)
        if len(rows)!=len(ids):raise ValueError('Saved holdout tile identities differ.')
        reproduced=evaluate_tiles(archive,rows,bundle['model'],bundle['threshold'])
    if reproduced!=entry['metrics']['test']:raise ValueError('Saved flood evaluation replay mismatch.')
    return {'model_id':MODEL_ID,'artifact_valid':True,'evaluation_reproduced':True,'metrics':reproduced}
