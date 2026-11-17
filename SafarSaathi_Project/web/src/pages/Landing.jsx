import React from 'react';
import { api } from '../api.js';
import { useQuery } from '../hooks.js';

// Garhwal skyline. Peaks are stylised but placed in real west-to-east order.
const PEAKS = [
  { x: 330, y: 118, name: 'Kedarnath', h: '6,940 m' },
  { x: 560, y: 92, name: 'Chaukhamba', h: '7,138 m' },
  { x: 905, y: 104, name: 'Trishul', h: '7,120 m' },
  { x: 1085, y: 62, name: 'Nanda Devi', h: '7,816 m' },
];
const FAR = 'M0 300 L90 250 L170 268 L250 190 L330 118 L400 196 L470 150 L560 92 L640 182 L720 160 L800 210 L905 104 L980 176 L1085 62 L1170 170 L1250 140 L1340 210 L1440 180 L1440 420 L0 420Z';
const MID = 'M0 330 L120 290 L210 312 L300 250 L380 286 L470 236 L560 280 L660 240 L760 290 L860 248 L960 296 L1060 250 L1160 300 L1270 262 L1360 300 L1440 280 L1440 420 L0 420Z';
const NEAR = 'M0 372 L140 340 L260 362 L380 326 L520 360 L650 334 L790 366 L930 336 L1070 368 L1210 340 L1340 364 L1440 350 L1440 420 L0 420Z';
const RIDGE = FAR.replace(/ L1440 420 L0 420Z$/, '');

function Skyline() {
  return (
    <svg viewBox="0 0 1440 420" preserveAspectRatio="xMidYMax slice" className="absolute inset-x-0 bottom-0 h-[clamp(240px,46vh,480px)] w-full" aria-hidden>
      <defs>
        <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#12151c" /><stop offset="1" stopColor="#0b0d12" />
        </linearGradient>
      </defs>
      <path d={FAR} fill="#151922" />
      <path d={RIDGE} fill="none" stroke="#e8bd4f" strokeWidth="1.6" strokeLinejoin="round" className="ridge-draw" />
      {PEAKS.map(p => (
        <g key={p.name} className="peak-label">
          <line x1={p.x} y1={p.y - 8} x2={p.x} y2={p.y - 42} stroke="#a39f92" strokeOpacity=".5" />
          <text x={p.x} y={p.y - 62} textAnchor="middle" fill="#ebe7dc" fontSize="15" fontFamily="var(--font-display)">{p.name}</text>
          <text x={p.x} y={p.y - 46} textAnchor="middle" fill="#a39f92" fontSize="12">{p.h}</text>
        </g>
      ))}
      <path d={MID} fill="#11141b" stroke="#e8bd4f" strokeOpacity=".14" />
      <path d={NEAR} fill="#0b0d12" stroke="#e8bd4f" strokeOpacity=".08" />
    </svg>
  );
}

function Status() {
  const q = useQuery('health', api.health);
  const ok = q.data?.status === 'ok';
  return (
    <p className="mt-8 flex items-center gap-2 text-sm text-mist">
      <span className={`h-2 w-2 rounded-full ${ok ? 'bg-moss' : q.loading ? 'bg-gold animate-pulse' : 'bg-ember'}`} aria-hidden />
      {ok ? `Backend online with ${q.data.trained_models} saved models ready to answer` : q.loading ? 'Checking the backend…' : 'Backend offline. Start the server to use the console.'}
    </p>
  );
}

// Core principle from the project report.
const PRINCIPLE = ['Predict', 'Simulate', 'Optimise', 'Explain', 'Support human action'];

const QUESTIONS = [
  { href: '#/tourism', tone: 'text-gold', q: 'How many visitors are coming?', a: 'Annual and monthly arrival forecasts trained on World Bank and Ministry of Tourism series, with each model\'s held-out test error shown next to its numbers.' },
  { href: '#/hazards', tone: 'text-ember', q: 'What hazards does the season carry?', a: 'The IBTrACS cyclone archive for the North Indian Ocean, and 25 years of daily NASA POWER climate for 29 Uttarakhand towns, shrines and parks.' },
  { href: '#/flood', tone: 'text-glacier', q: 'Where is the water?', a: 'A gradient-boosting model trained on the STURM-Flood benchmark marks water and flood extent pixel by pixel in Sentinel-1 radar tiles.' },
  { href: '#/reviews', tone: 'text-snow', q: 'What are visitors saying?', a: 'A TF-IDF and linear classifier sorts reviews into positive and negative. It was trained on hotel reviews, so results on Indian destinations are indicative.' },
  { href: '#/twin', tone: 'text-gold', q: 'How stressed is each destination?', a: 'A digital twin of 28 destinations scores visitor load, growth, monsoon exposure, heavy rain and altitude in a transparent index. Change the weights or add 30% more visitors and it recomputes.' },
  { href: '#/hotspots', tone: 'text-glacier', q: 'Which years broke the pattern?', a: 'Hotspot clustering shows where visitors concentrate; anomaly detection flags unusual visitor and rainfall years, and is checked against the 2013 disaster and COVID.' },
  { href: '#/routing', tone: 'text-ember', q: 'If a road closes, which way is safer?', a: 'Risk-aware routing on the OpenStreetMap road network compares the fastest route with one that also weighs hazard exposure, road vulnerability and congestion.' },
  { href: '#/optimizer', tone: 'text-moss', q: 'Where should visitors go instead?', a: 'Genetic-algorithm and particle-swarm solvers spread visitors across sites to balance crowding against hazard exposure, with a fixed seed so runs repeat.' },
];

// Adapted from the demonstration workflow in Appendix B of the project report.
const FLOW = [
  ['#/tourism', 'Forecast demand', 'Start from the arrivals forecast and check its error against the held-out test period.'],
  ['#/twin', 'Raise demand by 30%', 'Update the digital twin and see which destinations move into a higher stress band, and why.'],
  ['#/optimizer', 'Optimise', 'Compare GA and PSO allocations across sites and look at the trade-off each one makes.'],
  ['#/routing', 'Close a road', 'Simulate a landslide closure and compare the shortest route with the risk-aware alternative.'],
  ['#/reports', 'Brief the authority', 'Generate a report with model versions and sources, with simulated outputs marked as such.'],
];

const USERS = ['Tourism authorities and destination managers', 'District administration', 'Emergency planners', 'Local businesses and communities', 'Researchers'];

const SOURCES = [
  ['World Bank', 'International arrivals, India, 1995 onwards'],
  ['Ministry of Tourism', 'Monthly foreign tourist arrivals'],
  ['NASA POWER', 'Daily climate for 29 locations, 2000–2024'],
  ['IBTrACS', 'North Indian Ocean cyclone tracks'],
  ['STURM-Flood', 'Sentinel-1 radar tiles for flood mapping'],
  ['UTDB', 'Visitors to 28 Uttarakhand destinations, 2000–2024'],
  ['OpenStreetMap', 'Road network for routing, and the base map'],
];

export default function Landing() {
  return (
    <div className="min-h-full bg-ink">
      <header className="relative z-10 mx-auto flex max-w-[1180px] items-center justify-between px-5 py-5 md:px-8">
        <a href="#/" className="flex items-center gap-3">
          <img src="/logo-mark.png" alt="" className="h-10 w-10" />
          <span className="font-display text-lg font-semibold">SafarSaathi</span>
        </a>
        <nav className="flex items-center gap-5 text-sm">
          <a href="#questions" className="hidden text-mist hover:text-snow sm:inline">What it answers</a>
          <a href="#demo" className="hidden text-mist hover:text-snow sm:inline">Demo</a>
          <a href="#sources" className="hidden text-mist hover:text-snow sm:inline">Data</a>
          <a href="#/overview" className="rounded-lg border border-gold/50 px-3 py-1.5 font-semibold text-gold hover:bg-gold/10">Open the console</a>
        </nav>
      </header>

      <section className="relative -mt-[76px] flex min-h-[max(92vh,760px)] items-start overflow-hidden pt-[76px]">
        <Skyline />
        <div className="relative z-10 mx-auto w-full max-w-[1180px] px-5 pb-[clamp(240px,46vh,480px)] pt-[7vh] md:px-8">
          <p className="font-display text-[15px] font-medium text-gold">AI-Powered Tourism Intelligence &amp; Resilience Platform</p>
          <h1 className="mt-3 max-w-[16ch] font-display text-[clamp(2.6rem,6vw,5rem)] font-semibold leading-[1.02] tracking-[-0.03em]">
            Plan the season the mountains will actually have.
          </h1>
          <p className="mt-6 max-w-[58ch] text-[17px] leading-relaxed text-mist">
            SafarSaathi is a destination-level decision-support system for Uttarakhand. It puts visitor demand next to
            capacity, climate, flood and cyclone evidence, so destination managers can test a scenario before the season
            arrives and compare interventions, with a person making the final call.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <a href="#/overview" className="rounded-lg bg-gold px-5 py-2.5 font-semibold text-ink hover:brightness-110">Open the console</a>
            <a href="#/models" className="rounded-lg border border-line bg-ink/60 px-5 py-2.5 font-semibold text-snow backdrop-blur hover:border-mist">See the models</a>
          </div>
          <Status />
        </div>
      </section>

      <section className="border-b border-line" aria-label="Core principle">
        <ol className="mx-auto flex max-w-[1180px] flex-wrap items-center gap-x-3 gap-y-2 px-5 py-6 md:px-8">
          {PRINCIPLE.map((p, i) => (
            <li key={p} className="flex items-center gap-3 font-display text-[clamp(1rem,1.6vw,1.2rem)] font-medium">
              <span className={i === PRINCIPLE.length - 1 ? 'text-gold' : 'text-snow'}>{p}</span>
              {i < PRINCIPLE.length - 1 && <span className="h-px w-8 bg-gold/50" aria-hidden />}
            </li>
          ))}
        </ol>
      </section>

      <section id="questions" className="mx-auto max-w-[1180px] scroll-mt-6 px-5 py-20 md:px-8">
        <h2 className="max-w-[26ch] text-[clamp(1.6rem,3vw,2.3rem)] font-semibold">Eight questions a hill-state planner asks every season</h2>
        <div className="mt-10 grid gap-x-12 md:grid-cols-2">
          {QUESTIONS.map(item => (
            <a key={item.q} href={item.href} className="group border-t border-line py-7">
              <h3 className={`text-xl font-semibold ${item.tone}`}>{item.q}</h3>
              <p className="mt-2 max-w-[52ch] text-mist">{item.a}</p>
              <span className="mt-3 inline-block text-sm font-semibold text-snow/80 group-hover:text-gold">Go to this page</span>
            </a>
          ))}
        </div>
        <p className="mt-10 max-w-[80ch] text-mist">
          <span className="text-snow">Built for </span>{USERS.join(', ').replace(/, ([^,]*)$/, ' and $1').toLowerCase().replace(/^./, c => c.toUpperCase())}.
        </p>
      </section>

      <section id="demo" className="scroll-mt-6 border-y border-line bg-slate">
        <div className="mx-auto max-w-[1180px] px-5 py-20 md:px-8">
          <h2 className="text-[clamp(1.6rem,3vw,2.3rem)] font-semibold">The demo, from forecast to briefing</h2>
          <p className="mt-3 max-w-[62ch] text-mist">Follows the demonstration workflow in the project report. Scenario and optimiser results are simulated estimates, not observed outcomes.</p>
          <ol className="relative mt-12 grid gap-10 md:grid-cols-5 md:gap-6">
            <div className="absolute left-0 right-0 top-[7px] hidden h-px bg-gradient-to-r from-gold via-ember to-moss md:block" aria-hidden />
            {FLOW.map(([href, t, d]) => (
              <li key={t} className="relative">
                <span className="relative block h-[15px] w-[15px] rounded-full border-2 border-gold bg-slate" aria-hidden />
                <a href={href} className="mt-4 block text-lg font-semibold hover:text-gold">{t}</a>
                <p className="mt-1 text-sm text-mist">{d}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section id="sources" className="mx-auto grid max-w-[1180px] scroll-mt-6 gap-12 px-5 py-20 md:grid-cols-[1fr_1.3fr] md:px-8">
        <div>
          <h2 className="text-[clamp(1.6rem,3vw,2.3rem)] font-semibold">Decision support, honest about its limits</h2>
          <p className="mt-4 max-w-[48ch] text-mist">
            Every model is trained ahead of time and loaded from disk; nothing is retrained when you click. SafarSaathi does
            not claim to predict sudden disasters or replace emergency authorities. Where outcome data doesn't exist yet, like
            a ground truth for destination stress, the model stays switched off and the console shows the raw indicators instead.
          </p>
          <blockquote className="mt-8 border-l-2 border-gold pl-4 font-display text-lg leading-snug text-snow">
            A successful destination is not necessarily one that maximises tourist numbers.
          </blockquote>
          <a href="#/data-hub" className="mt-8 inline-block text-sm font-semibold text-gold hover:underline">Browse the data hub</a>
        </div>
        <dl className="divide-y divide-line self-start border-y border-line">
          {SOURCES.map(([k, v]) => (
            <div key={k} className="grid grid-cols-[minmax(0,11rem)_1fr] gap-4 py-4">
              <dt className="font-display font-semibold">{k}</dt>
              <dd className="text-mist">{v}</dd>
            </div>
          ))}
        </dl>
      </section>

      <footer className="border-t border-line">
        <div className="mx-auto flex max-w-[1180px] flex-wrap items-center justify-between gap-6 px-5 py-10 md:px-8">
          <div className="flex items-center gap-4">
            <img src="/logo-full.png" alt="SafarSaathi" className="h-20 w-auto" />
            <p className="max-w-[34ch] text-sm text-mist">AI-Powered Tourism Intelligence &amp; Resilience Platform. An AIML team project at Bennett University.</p>
          </div>
          <a href="#/overview" className="font-semibold text-gold hover:underline">Open the console</a>
        </div>
      </footer>
    </div>
  );
}
