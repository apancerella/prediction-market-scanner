import { useEffect, useMemo, useState } from "react";
import type { Ledger, Opinion, Opinions, Opportunity, Scan, Verdict } from "./types";
import { cents, etTime, pct, timeAgo, timeUntil, usd } from "./format";
import { Sparkline } from "./Sparkline";

type Tab = "picks" | "record" | "how";
type Sort = "likely" | "soonest" | "profit" | "return";

// The Claude artifact build embeds the data in the page (artifacts can't fetch other sites).
const EMBEDDED = (window as unknown as { __PMS_DATA__?: Record<string, unknown> }).__PMS_DATA__;

async function getJson<T>(path: string): Promise<T | null> {
  if (EMBEDDED) {
    const name = path.split("/").pop()!.replace(".json", "");
    return (EMBEDDED[name] as T) ?? null;
  }
  try {
    const r = await fetch(`${path}?t=${Date.now()}`, { cache: "no-store" });
    return r.ok ? ((await r.json()) as T) : null;
  } catch {
    return null;
  }
}

const VERDICT: Record<Verdict, { label: string; icon: string }> = {
  strong: { label: "Strong", icon: "▲" },
  reasonable: { label: "Reasonable", icon: "●" },
  pass: { label: "Pass", icon: "✕" },
};

export default function App() {
  const [scan, setScan] = useState<Scan | null>(null);
  const [ledger, setLedger] = useState<Ledger | null>(null);
  const [opinions, setOpinions] = useState<Opinions | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [tab, setTab] = useState<Tab>(() => (location.hash.slice(1) as Tab) || "picks");

  useEffect(() => {
    Promise.all([
      getJson<Scan>("data/latest.json"),
      getJson<Ledger>("data/picks.json"),
      getJson<Opinions>("data/opinions.json"),
    ]).then(([s, l, o]) => {
      setScan(s);
      setLedger(l);
      setOpinions(o);
      setLoaded(true);
    });
  }, []);

  useEffect(() => {
    history.replaceState(null, "", `#${tab}`);
  }, [tab]);

  const stale = scan && Date.now() - new Date(scan.generated_at).getTime() > 3 * 3_600_000;

  return (
    <div className="page">
      <header className="top">
        <div>
          <h1>Prediction Market Scanner</h1>
          <p className="muted">
            High-probability picks from the exchange behind Robinhood's prediction markets, with what a $
            {Math.round(scan?.stake ?? 100)} bet would return.
          </p>
        </div>
        <div className="updated">
          {scan ? (
            <>
              <span className={stale ? "chip warn" : "chip"}>
                {stale ? "⚠ Data is stale · " : ""}Scanned {timeAgo(scan.generated_at)}
              </span>
              <span className="muted small">{scan.markets_scanned.toLocaleString()} markets checked</span>
            </>
          ) : null}
        </div>
      </header>

      <nav className="tabs" role="tablist">
        {(
          [
            ["picks", "Opportunities"],
            ["record", "Track record"],
            ["how", "How it works"],
          ] as [Tab, string][]
        ).map(([t, label]) => (
          <button key={t} role="tab" aria-selected={tab === t} className={tab === t ? "on" : ""} onClick={() => setTab(t)}>
            {label}
          </button>
        ))}
      </nav>

      {!loaded ? (
        <p className="muted">Loading…</p>
      ) : !scan ? (
        <div className="empty">
          <h2>No scan data yet</h2>
          <p>
            Run <code>cd scanner && python -m pms.scan</code> locally, or wait for the scheduled GitHub Action to
            publish its first scan.
          </p>
        </div>
      ) : tab === "picks" ? (
        <Picks scan={scan} ledger={ledger} opinions={opinions} />
      ) : tab === "record" ? (
        <Record ledger={ledger} />
      ) : (
        <How scan={scan} />
      )}

      <footer className="muted small">
        Not financial advice. Prices come from Kalshi's public data; the markets Robinhood lists and its prices can
        differ, so confirm in the Robinhood app before betting. A high price means the market expects a win; it is
        not a guarantee.
      </footer>
    </div>
  );
}

function Picks({ scan, ledger, opinions }: { scan: Scan; ledger: Ledger | null; opinions: Opinions | null }) {
  const [q, setQ] = useState("");
  const [cat, setCat] = useState("all");
  const [strategy, setStrategy] = useState("all");
  const [minProb, setMinProb] = useState(85);
  const [maxDays, setMaxDays] = useState(7);
  const [verdict, setVerdict] = useState<"all" | Verdict | "reviewed">("all");
  const [sort, setSort] = useState<Sort>("likely");

  const cats = useMemo(() => {
    const c = new Map<string, number>();
    scan.opportunities.forEach((o) => c.set(o.category, (c.get(o.category) ?? 0) + 1));
    return [...c.entries()].sort((a, b) => b[1] - a[1]);
  }, [scan]);

  const list = useMemo(() => {
    const needle = q.trim().toLowerCase();
    const out = scan.opportunities.filter((o) => {
      const op = opinions?.picks[o.id];
      if (cat !== "all" && o.category !== cat) return false;
      if (strategy !== "all" && o.strategy !== strategy) return false;
      if (o.implied_prob * 100 < minProb) return false;
      if ((o.days_to_settle ?? 0) > maxDays) return false;
      if (verdict === "reviewed" && !op) return false;
      if (verdict !== "all" && verdict !== "reviewed" && op?.verdict !== verdict) return false;
      if (needle && !`${o.title} ${o.outcome} ${o.category} ${o.tags.join(" ")}`.toLowerCase().includes(needle))
        return false;
      return true;
    });
    const key: Record<Sort, (o: Opportunity) => number> = {
      likely: (o) => -o.score,
      soonest: (o) => o.days_to_settle ?? 99,
      profit: (o) => -o.bet.profit,
      return: (o) => -(o.bet.return_pct / Math.max(o.days_to_settle ?? 0, 0.5)),
    };
    return out.sort((a, b) => key[sort](a) - key[sort](b));
  }, [scan, opinions, q, cat, strategy, minProb, maxDays, verdict, sort]);

  const reviewed = opinions ? Object.keys(opinions.picks).length : 0;
  const strong = opinions ? Object.values(opinions.picks).filter((p) => p.verdict === "strong").length : 0;
  const s = ledger?.summary;

  return (
    <>
      <section className="tiles">
        <Tile label="Opportunities now" value={String(scan.opportunities.length)} note={`from ${scan.markets_scanned.toLocaleString()} markets`} />
        <Tile
          label="Claude's review"
          value={opinions ? `${strong} strong` : "Not yet"}
          note={opinions ? `${reviewed} reviewed · ${timeAgo(opinions.generated_at)}` : "Runs twice a day"}
        />
        <Tile
          label="Past picks won"
          value={s?.win_rate != null ? pct(s.win_rate * 100, 0) : "—"}
          note={s?.resolved ? `${s.wins} of ${s.resolved} settled` : "No settled picks yet"}
        />
        <Tile
          label="If you'd bet every pick"
          value={s?.resolved ? usd(s.profit, true) : "—"}
          note={s?.resolved ? `on ${usd(s.staked)} staked` : "Tracks once picks settle"}
        />
      </section>

      {opinions?.summary ? (
        <section className="review-summary">
          <strong>Claude's latest take</strong> <span className="muted small">· {etTime(opinions.generated_at)}</span>
          <p>{opinions.summary}</p>
        </section>
      ) : null}

      <section className="filters">
        <input type="search" placeholder="Search team, player, topic…" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search" />
        <select value={cat} onChange={(e) => setCat(e.target.value)} aria-label="Category">
          <option value="all">All categories</option>
          {cats.map(([c, n]) => (
            <option key={c} value={c}>
              {c} ({n})
            </option>
          ))}
        </select>
        <select value={strategy} onChange={(e) => setStrategy(e.target.value)} aria-label="Type">
          <option value="all">All types</option>
          <option value="favorite">Favorites</option>
          <option value="arbitrage">Arbitrage</option>
        </select>
        <select value={verdict} onChange={(e) => setVerdict(e.target.value as typeof verdict)} aria-label="Claude verdict">
          <option value="all">Any verdict</option>
          <option value="reviewed">Reviewed by Claude</option>
          <option value="strong">Strong only</option>
          <option value="reasonable">Reasonable only</option>
          <option value="pass">Pass only</option>
        </select>
        <label className="range">
          Chance ≥ {minProb}%
          <input type="range" min={85} max={99} value={minProb} onChange={(e) => setMinProb(+e.target.value)} />
        </label>
        <label className="range">
          Settles ≤ {maxDays}d
          <input type="range" min={1} max={7} value={maxDays} onChange={(e) => setMaxDays(+e.target.value)} />
        </label>
        <select value={sort} onChange={(e) => setSort(e.target.value as Sort)} aria-label="Sort">
          <option value="likely">Most likely first</option>
          <option value="soonest">Settles soonest</option>
          <option value="profit">Biggest $ profit</option>
          <option value="return">Best return per day</option>
        </select>
      </section>

      <p className="muted small">
        Showing {list.length} of {scan.opportunities.length}
      </p>

      <section className="cards">
        {list.map((o) => (
          <Card key={o.id} o={o} op={opinions?.picks[o.id]} samples={ledger?.picks[o.id]?.samples ?? []} />
        ))}
        {list.length === 0 ? <div className="empty">Nothing matches these filters.</div> : null}
      </section>
    </>
  );
}

function Tile({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <div className="tile">
      <div className="tile-label">{label}</div>
      <div className="tile-value">{value}</div>
      <div className="tile-note muted small">{note}</div>
    </div>
  );
}

function Card({ o, op, samples }: { o: Opportunity; op?: Opinion; samples: [string, number][] }) {
  const [open, setOpen] = useState(false);
  const b = o.bet;
  return (
    <article className="card">
      <div className="card-head">
        <span className="chip">{o.category}</span>
        {o.strategy === "arbitrage" ? <span className="chip accent">Arbitrage</span> : null}
        {o.in_progress ? <span className="chip warn">⚠ Live</span> : null}
        {op ? (
          <span className={`verdict v-${op.verdict}`}>
            {VERDICT[op.verdict].icon} Claude: {VERDICT[op.verdict].label}
          </span>
        ) : null}
      </div>
      <h3>{o.outcome}</h3>
      <p className="muted title">{o.title}</p>

      <div className="facts">
        <div>
          <span className="k">Market's chance</span>
          <span className="v">{pct(o.implied_prob * 100, 0)}</span>
        </div>
        <div>
          <span className="k">Price</span>
          <span className="v">{cents(o.price)}</span>
        </div>
        <div>
          <span className="k">Settles in</span>
          <span className="v">{o.in_progress ? "settling" : timeUntil(o.settles_at)}</span>
        </div>
      </div>

      <div className="bet">
        <div className="bet-title">
          ${Math.round(b.stake)} bet · {b.contracts} contracts
        </div>
        <div className="bet-row win">
          <span>✓ If it wins</span>
          <strong>{usd(b.profit, true)}</strong>
          <span className="muted small">{pct(b.return_pct, 2)} return</span>
        </div>
        <div className="bet-row lose">
          <span>✕ If it loses</span>
          <strong>{usd(-b.max_loss, true)}</strong>
          <span className="muted small">needs {pct(b.breakeven_prob * 100, 1)} to break even</span>
        </div>
        <div className="muted small">
          Cost {usd(b.cost)} + {usd(b.fees)} fees = {usd(b.total_cost)} · pays {usd(b.payout)}
        </div>
      </div>

      {op ? (
        <div className="opinion">
          <p>{op.reason}</p>
          {op.claude_prob != null ? (
            <p className="small">
              Claude's estimate: <strong>{pct(op.claude_prob * 100, 0)}</strong> vs market {pct(o.implied_prob * 100, 0)}
            </p>
          ) : null}
          {op.red_flags?.length ? (
            <ul className="flags">
              {op.red_flags.map((f) => (
                <li key={f}>⚠ {f}</li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}

      {o.flags.length ? (
        <ul className="flags">
          {o.flags.map((f) => (
            <li key={f}>⚠ {f}</li>
          ))}
        </ul>
      ) : null}

      <Sparkline samples={samples} />

      <div className="card-foot">
        <button className="link" onClick={() => setOpen(!open)} aria-expanded={open}>
          {open ? "Hide details" : "Details & rules"}
        </button>
        <a href={o.url} target="_blank" rel="noreferrer">
          View on Kalshi ↗
        </a>
      </div>
      {open ? (
        <div className="details small">
          {o.legs ? (
            <ul>
              {o.legs.map((l) => (
                <li key={l.ticker}>
                  YES {l.outcome} @ {cents(l.price)}
                </li>
              ))}
            </ul>
          ) : null}
          <p>{o.rules || "No rules text provided."}</p>
          <p className="muted">
            Settles {etTime(o.settles_at)} · 24h volume {Math.round(o.volume_24h).toLocaleString()} · spread{" "}
            {o.spread != null ? cents(o.spread) : "—"} · {o.ticker}
          </p>
          <p className="muted">In Robinhood: open Prediction Markets and search “{o.title}”.</p>
        </div>
      ) : null}
    </article>
  );
}

function Record({ ledger }: { ledger: Ledger | null }) {
  if (!ledger) return <div className="empty">No track record yet. It fills in as picks settle.</div>;
  const s = ledger.summary;
  const settled = Object.values(ledger.picks)
    .filter((p) => p.result)
    .sort((a, b) => (b.result!.settled_seen > a.result!.settled_seen ? 1 : -1));
  return (
    <>
      <p className="muted">
        Every pick is scored with the {usd(Object.values(ledger.picks)[0]?.first_bet.stake ?? 100)} bet from the
        moment it first appeared. This is the honest check on whether "easy wins" actually win.
      </p>
      <section className="tiles">
        <Tile label="Settled picks" value={String(s.resolved)} note={`${s.tracked} being tracked`} />
        <Tile label="Win rate" value={s.win_rate != null ? pct(s.win_rate * 100, 1) : "—"} note={`${s.wins} wins`} />
        <Tile label="Total profit" value={usd(s.profit, true)} note={`on ${usd(s.staked)} staked`} />
        <Tile label="Return" value={pct(s.roi_pct, 2)} note="profit ÷ staked" />
      </section>
      {Object.keys(s.by_strategy).length ? (
        <table className="table">
          <thead>
            <tr>
              <th>Type</th>
              <th>Settled</th>
              <th>Won</th>
              <th>Profit</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(s.by_strategy).map(([k, v]) => (
              <tr key={k}>
                <td>{k}</td>
                <td>{v.resolved}</td>
                <td>{pct((v.wins / v.resolved) * 100, 1)}</td>
                <td>{usd(v.profit, true)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
      <h2>Recently settled</h2>
      {settled.length === 0 ? (
        <div className="empty">Nothing has settled yet.</div>
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Pick</th>
                <th>Price</th>
                <th>Result</th>
                <th>P&amp;L</th>
              </tr>
            </thead>
            <tbody>
              {settled.slice(0, 200).map((p) => (
                <tr key={p.id}>
                  <td>
                    <div>{p.outcome}</div>
                    <div className="muted small">{p.title}</div>
                  </td>
                  <td>{cents(p.first_price)}</td>
                  <td className={p.result!.won ? "good" : "bad"}>{p.result!.won ? "✓ Won" : "✕ Lost"}</td>
                  <td>{usd(p.result!.profit, true)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

function How({ scan }: { scan: Scan }) {
  const f = scan.criteria.favorites as Record<string, number>;
  return (
    <section className="prose">
      <h2>Where the data comes from</h2>
      <p>
        Robinhood's prediction markets are event contracts traded on Kalshi. Robinhood has no public API for them, so
        the scanner reads Kalshi's public market data. Robinhood may not list every market shown here, and its prices
        can differ slightly, so check the Robinhood app before you bet.
      </p>
      <h2>What counts as an easy win</h2>
      <ul>
        <li>
          <strong>Favorites:</strong> contracts priced {cents(f.min_price)}–{cents(f.max_price)} (the market gives
          them roughly an {Math.round(f.min_price * 100)}–{Math.round(f.max_price * 100)}% chance) that settle within{" "}
          {f.max_days_to_settle} days, with at least {f.min_volume_24h} contracts traded in the last day and a spread
          of {cents(f.max_spread)} or less.
        </li>
        <li>
          <strong>Arbitrage:</strong> events where exactly one outcome must win and buying YES on every outcome costs
          less than $1 after fees. These are rare and close fast.
        </li>
      </ul>
      <h2>How the {usd(scan.stake)} estimate works</h2>
      <p>
        Each contract pays $1.00 if it wins and nothing if it loses. The scanner buys as many whole contracts as{" "}
        {usd(scan.stake)} covers after fees (Robinhood charges about 1¢ commission plus about 1¢ exchange fee per
        contract). Profit is the payout minus everything you spent. If it loses, you lose everything you spent.
      </p>
      <p>
        Break-even chance is how often the pick must win for betting it every time to make money. If the market's
        chance is right, expected profit is roughly zero minus fees. These picks only make money if the real chance
        is higher than the price says.
      </p>
      <h2>Claude's review</h2>
      <p>
        Twice a day, a scheduled Claude Code session reads the latest picks, researches them (news, injuries, data
        releases, rule wording) and labels each one Strong, Reasonable or Pass, with its own estimate of the chance.
        It's a second opinion, not a guarantee. It does not place trades.
      </p>
    </section>
  );
}
