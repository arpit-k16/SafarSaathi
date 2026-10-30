"""Synthetic fixture tests only. Real benchmark training is verified separately."""
import io
import json
import zipfile

import numpy as np
import pandas as pd
import pytest
import tifffile

from safarsaathi_ml.flood_baseline import confusion_metrics,image_features,read_pair,segment,segment_geotiff,split_metadata,train_flood
from safarsaathi_ml.pipeline import sha256


def metadata_fixture(n=12):
    return pd.DataFrame({'tile_id':[f'tile_{i}.tif' for i in range(n)],'ems_code':[f'event_{i}' for i in range(n)],
        'country':[f'country_{i}' for i in range(n)],'epsg_code':32632,'sentinel_date':'2020-01-01 00:00:00','floodmap_date':'2020-01-01 00:00:00'})


def test_country_event_splits_and_invalid_metadata():
    data=metadata_fixture();splits,groups,_=split_metadata(data)
    for left,right in [('train','test'),('train','validation'),('validation','test')]:
        assert not set(splits[left].country)&set(splits[right].country)
        assert not set(splits[left].ems_code)&set(splits[right].ems_code)
    with pytest.raises(ValueError):split_metadata(pd.concat([data,data.iloc[:1]]))
    with pytest.raises(ValueError):split_metadata(data.assign(floodmap_date='2020-02-01'))


def test_image_and_metric_contracts():
    assert image_features(np.zeros((128,128,2))).shape==(16384,7)
    for image in (np.zeros((127,128,2)),np.full((128,128,2),np.nan),np.full((128,128,2),100)):
        with pytest.raises(ValueError):image_features(image)
    score=confusion_metrics([80,10,5,20]);assert score['IoU']==20/35 and score['Dice_F1']==40/55
    assert confusion_metrics([100,0,0,0])['IoU'] is None


def test_synthetic_training_reload_and_geotiff(tmp_path):
    (tmp_path/'models').mkdir();data=tmp_path/'synthetic_data';data.mkdir()
    metadata=metadata_fixture();archive=data/'Dataset.zip';rng=np.random.default_rng(9)
    tags=[(33550,'d',3,(10.,10.,0.),False),(33922,'d',6,(0.,0.,0.,500000.,4000000.,0.),False),
          (34735,'H',8,(1,1,0,1,3072,0,1,32632),False)]
    first_bytes=None
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as zipped:
        zipped.writestr('Dataset/Sentinel1_metadata.csv',metadata.to_csv(index=False))
        for row in metadata.itertuples():
            image=rng.random((128,128,2)).astype(np.float32);mask=np.where(image[:,:,0]<.3,5,0).astype(np.uint8)
            for category,array in [('S1',image),('Floodmaps',mask)]:
                stream=io.BytesIO();tifffile.imwrite(stream,array,extratags=tags,metadata=None)
                content=stream.getvalue();zipped.writestr('Dataset/Sentinel1/'+category+'/'+row.tile_id,content)
                if first_bytes is None:first_bytes=content
    (data/'download_verification.json').write_text(json.dumps({'publisher_checksum_matched':True,'bytes':archive.stat().st_size,'sha256':sha256(archive),'md5':'SYNTHETIC UNIT TEST FIXTURE'}))
    (tmp_path/'data/interim').mkdir(parents=True)
    entry=train_flood(tmp_path,data)
    assert entry['training_completed']
    result=segment(tmp_path,{'image':np.zeros((128,128,2)).tolist(),'metadata':{'source_format':'STURM-S1-preprocessed','geo_tags':{}}})
    assert len(result['mask'])==128 and len(result['confidence_map'])==128
    source=tmp_path/'fixture.tif';source.write_bytes(first_bytes);target=tmp_path/'predicted.tif'
    assert segment_geotiff(tmp_path,source,target)['geospatial_metadata_preserved']
    with pytest.raises(ValueError):segment_geotiff(tmp_path,source,target)
    with pytest.raises(ValueError):segment(tmp_path,{'image':np.zeros((128,128,2)).tolist(),'metadata':{'source_format':'STURM-S1-preprocessed','path':'../../secret'}})
