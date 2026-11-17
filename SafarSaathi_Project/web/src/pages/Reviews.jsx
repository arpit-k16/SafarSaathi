import React, { useState } from 'react';
import { api, fmt } from '../api.js';
import { useAction, useQuery } from '../hooks.js';
import { Button, ErrorNotice, Field, Grid, Notes, Page, Panel, Pill, Query, Select, Stat, Table, inputClass } from '../components/ui.jsx';

const EXAMPLE = [
  'The room had a clear view of the river and the staff arranged an early taxi for the Kedarnath trek.',
  'Water leaked through the ceiling all night and nobody at the front desk answered the phone.',
  'Clean, quiet and close to the ghats. Breakfast was simple but fresh.',
].join('\n');

export default function Reviews() {
  const models = useQuery('models', api.models);
  const [modelId, setModelId] = useState('');
  const [text, setText] = useState(EXAMPLE);
  const action = useAction();
  const reviews = text.split('\n').map(s => s.trim()).filter(Boolean);
  const tooMany = reviews.length > 100;
  return (
    <Page title="Review insights" intro="Classifies visitor reviews as positive or negative with the saved TF-IDF + linear classifier. It was trained on a global hotel-review corpus, so treat results on Indian destination reviews as indicative.">
      <Query q={models}>{list => {
        const reviewModels = list.filter(m => m.task === 'review classification');
        const chosen = reviewModels.find(m => m.model_id === modelId) || reviewModels[0];
        if (!chosen) return <Panel title="No review model registered"><p className="text-sm text-mist">The registry has no review-classification model.</p></Panel>;
        const report = chosen.metrics.classification_report || {};
        const submit = () => action.run(() => api.classify(chosen.model_id, reviews));
        const pos = action.data?.predictions.filter(p => p === 'POSITIVE').length ?? 0;
        return (
          <>
            <Grid cols={4}>
              <Stat label="Held-out accuracy" value={`${fmt(chosen.metrics.accuracy * 100, 1)}%`} note={`${fmt(report['macro avg']?.support, 0)} test reviews`} />
              <Stat label="Macro F1" value={fmt(chosen.metrics.macro_f1, 3)} />
              <Stat label="Negative recall" value={fmt(report.NEGATIVE?.recall, 3)} note="Complaints caught" tone="hazard" />
              <Stat label="Positive precision" value={fmt(report.POSITIVE?.precision, 3)} tone="good" />
            </Grid>
            <Panel title="Classify reviews" description="One review per line, up to 100. Text is sent to the backend for this request only and is not stored or logged.">
              <form onSubmit={e => { e.preventDefault(); if (!tooMany && reviews.length) submit(); }} className="flex flex-col gap-4">
                {reviewModels.length > 1 && <Field label="Model" className="max-w-sm"><Select value={chosen.model_id} onChange={e => setModelId(e.target.value)}>{reviewModels.map(m => <option key={m.model_id}>{m.model_id}</option>)}</Select></Field>}
                <Field label="Reviews" hint={`${reviews.length} review${reviews.length === 1 ? '' : 's'}${tooMany ? ' — remove some; the limit is 100' : ''}`}>
                  <textarea className={`${inputClass} min-h-40 font-sans`} value={text} onChange={e => setText(e.target.value)} />
                </Field>
                <div className="flex gap-3">
                  <Button type="submit" disabled={action.loading || !reviews.length || tooMany}>{action.loading ? 'Classifying…' : 'Classify reviews'}</Button>
                  <Button variant="secondary" onClick={() => { setText(''); action.reset(); }}>Clear</Button>
                </div>
              </form>
              <div className="mt-4"><ErrorNotice error={action.error} retry={submit} /></div>
              {action.data && (
                <div className="mt-5">
                  <div className="mb-3 flex flex-wrap gap-2"><Pill tone="good">{pos} positive</Pill><Pill tone="off">{action.data.predictions.length - pos} negative</Pill><Pill>Model {action.data.model_version}</Pill></div>
                  <Table columns={['Review', 'Label']} rows={action.data.predictions.map((p, i) => [reviews[i], <Pill tone={p === 'POSITIVE' ? 'ok' : 'off'}>{p.toLowerCase()}</Pill>])} />
                  <Notes items={[action.data.limitations]} />
                </div>
              )}
            </Panel>
            <Notes items={[chosen.limitations]} title="Model scope" />
          </>
        );
      }}</Query>
    </Page>
  );
}
