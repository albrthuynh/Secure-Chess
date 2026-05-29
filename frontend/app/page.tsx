"use client";

import { useEffect, useMemo, useRef, useState } from "react";

type Side = "w" | "b";

type Piece = {
  side: Side;
  role: string;
};

type EventTone = "ok" | "warn" | "info";

type DemoEvent = {
  id: number;
  time: string;
  tone: EventTone;
  text: string;
};

// Unicode chess symbols — much prettier than raw letters on the mini boards
const CHESS_SYMBOLS: Record<Side, Record<string, string>> = {
  w: { K: "♔", Q: "♕", R: "♖", B: "♗", N: "♘", P: "♙" },
  b: { K: "♚", Q: "♛", R: "♜", B: "♝", N: "♞", P: "♟" },
};

const files = ["a", "b", "c", "d", "e", "f", "g", "h"];
const ranks = ["8", "7", "6", "5", "4", "3", "2", "1"];

const moves = [
  ["e2", "e4"], ["e7", "e5"], ["g1", "f3"], ["b8", "c6"],
  ["f1", "b5"], ["a7", "a6"], ["b5", "a4"], ["g8", "f6"],
  ["e1", "g1"], ["f8", "e7"], ["f1", "e1"], ["b7", "b5"],
  ["a4", "b3"], ["d7", "d6"], ["c2", "c3"], ["e8", "g8"],
  ["h2", "h3"], ["c6", "b8"], ["d2", "d4"], ["b8", "d7"],
];

const baseEvents = [
  { tone: "info" as const, text: "Redis matchmaking paired players for rapid-10 queue" },
  { tone: "ok"   as const, text: "Signed match ticket verified by C++ game server" },
  { tone: "ok"   as const, text: "Legal move accepted and broadcast to both sockets" },
  { tone: "info" as const, text: "Move latency sample written to Prometheus histogram" },
  { tone: "ok"   as const, text: "Game result persisted through gRPC ReportGameEnd" },
  { tone: "warn" as const, text: "Invalid move rejected before board mutation" },
  { tone: "info" as const, text: "Resume token issued for disconnected player" },
  { tone: "ok"   as const, text: "Resume token consumed and room state replayed" },
];

const gameNames = [
  "Match A17", "Match B04", "Match C91", "Match D22",
  "Match E60", "Match F13", "Match G08", "Match H31",
];

function initialBoard() {
  const board: Record<string, Piece> = {};
  const backRank = ["R", "N", "B", "Q", "K", "B", "N", "R"];
  files.forEach((file, i) => {
    board[`${file}1`] = { side: "w", role: backRank[i] };
    board[`${file}2`] = { side: "w", role: "P" };
    board[`${file}7`] = { side: "b", role: "P" };
    board[`${file}8`] = { side: "b", role: backRank[i] };
  });
  return board;
}

function boardAfter(moveCount: number) {
  const board = initialBoard();
  moves.slice(0, moveCount).forEach(([from, to]) => {
    if (from === "e1" && to === "g1") {
      board.g1 = board.e1; board.f1 = board.h1;
      delete board.e1; delete board.h1;
      return;
    }
    if (from === "e8" && to === "g8") {
      board.g8 = board.e8; board.f8 = board.h8;
      delete board.e8; delete board.h8;
      return;
    }
    const piece = board[from];
    if (!piece) return;
    board[to] = piece;
    delete board[from];
  });
  return board;
}

function nowLabel() {
  return new Intl.DateTimeFormat("en", {
    hour: "2-digit", minute: "2-digit", second: "2-digit",
  }).format(new Date());
}

export default function Home() {
  const [running, setRunning]           = useState(false);
  const [tick, setTick]                 = useState(0);
  const [totalGames, setTotalGames]     = useState(100);
  const [concurrency, setConcurrency]   = useState(50);
  const [invalidMoveTest, setInvalidMoveTest] = useState(true);
  const [reconnectTest, setReconnectTest]     = useState(true);
  const tickRef = useRef(0);

  const [events, setEvents] = useState<DemoEvent[]>([{
    id: 0, time: nowLabel(), tone: "info",
    text: "Demo cockpit armed with the latest 100-game load profile",
  }]);

  useEffect(() => {
    if (!running) return;
    const id = window.setInterval(() => {
      tickRef.current += 1;
      const t = tickRef.current;
      const filtered = baseEvents.filter((e) => {
        if (!invalidMoveTest && e.text.includes("Invalid")) return false;
        if (!reconnectTest  && e.text.includes("Resume"))  return false;
        return true;
      });
      const event = filtered[t % filtered.length];
      setTick(t);
      setEvents((cur) => [{ id: t, time: nowLabel(), tone: event.tone, text: event.text }, ...cur].slice(0, 9));
    }, 620);
    return () => window.clearInterval(id);
  }, [running, invalidMoveTest, reconnectTest]);

  const maxMoves       = totalGames * 37;
  const simMoves       = Math.min(maxMoves, tick * Math.max(4, Math.round(concurrency / 3)));
  const gamesCompleted = Math.min(totalGames, Math.floor(simMoves / 37));
  const activeGames    = running ? Math.min(concurrency, totalGames - gamesCompleted) : 0;
  const sockets        = activeGames * 2;
  const p50  = running ? 1.2  + ((tick % 4) * 0.04) : 1.2;
  const p95  = running ? 5.06 + ((tick % 5) * 0.07) : 5.06;
  const p99  = running ? 7.09 + ((tick % 3) * 0.11) : 7.09;
  const pct  = Math.round((simMoves / maxMoves) * 100);

  const boards = useMemo(() => gameNames.map((name, i) => {
    const moveCount = (tick + i * 3) % moves.length;
    const latency   = (1.08 + ((tick + i) % 7) * 0.63).toFixed(2);
    return { name, latency, moveCount, board: boardAfter(moveCount), status: running ? "live" : "queued" };
  }), [tick, running]);

  return (
    <main className="demo-shell">
      {/* Hero */}
      <section className="hero-strip">
        <div>
          <p className="hero-eyebrow">Secure Chess — Demo Cockpit</p>
          <h1>Authoritative games<br />under load</h1>
        </div>
        <div className="hero-badge">
          <span className="hero-badge-label">p99 latency</span>
          <span className="hero-badge-value">{p99.toFixed(2)}ms</span>
        </div>
      </section>

      {/* Cockpit grid */}
      <div className="cockpit-grid">
        {/* Controls */}
        <aside className="panel control-panel">
          <div className="panel-header">
            <span className="panel-header-label">Load Profile</span>
            <span className="panel-header-value">{pct}%</span>
          </div>

          <button
            className={running ? "btn-run danger" : "btn-run"}
            onClick={() => setRunning((r) => !r)}
          >
            {running ? "Pause Demo" : "Start Load Demo"}
          </button>

          <label className="range-control">
            <span className="range-label">Total games</span>
            <span className="range-value">{totalGames}</span>
            <input type="range" min="20" max="160" step="10"
              value={totalGames} onChange={(e) => setTotalGames(Number(e.target.value))} />
          </label>

          <label className="range-control">
            <span className="range-label">Games in flight</span>
            <span className="range-value">{concurrency}</span>
            <input type="range" min="5" max="80" step="5"
              value={concurrency} onChange={(e) => setConcurrency(Number(e.target.value))} />
          </label>

          <label className="toggle-row">
            <input type="checkbox" checked={invalidMoveTest}
              onChange={(e) => setInvalidMoveTest(e.target.checked)} />
            <span className="toggle-label">Invalid move rejection</span>
          </label>

          <label className="toggle-row">
            <input type="checkbox" checked={reconnectTest}
              onChange={(e) => setReconnectTest(e.target.checked)} />
            <span className="toggle-label">Reconnect resume path</span>
          </label>

          <div className="run-profile">
            <span className="run-profile-key">Move delay</span>
            <span className="run-profile-val">120ms</span>
            <span className="run-profile-key">Moves / game</span>
            <span className="run-profile-val">37</span>
            <span className="run-profile-key">Join timeout</span>
            <span className="run-profile-val">30s</span>
          </div>
        </aside>

        {/* Game wall */}
        <section className="game-wall" aria-label="Live game wall">
          {boards.map((game) => (
            <article className="game-tile" key={game.name}>
              <div className="game-tile-header">
                <span className="game-tile-name">{game.name}</span>
                <span className="game-tile-latency">{game.latency}ms</span>
              </div>

              <div className="mini-board">
                {ranks.flatMap((rank, ri) =>
                  files.map((file, fi) => {
                    const sq    = `${file}${rank}`;
                    const piece = game.board[sq];
                    const light = (ri + fi) % 2 === 0;
                    return (
                      <div className={light ? "sq light" : "sq dark"} key={sq} aria-label={sq}>
                        {piece ? (
                          <span className={`piece-sym ${piece.side === "w" ? "white" : "black"}`}>
                            {CHESS_SYMBOLS[piece.side][piece.role] ?? piece.role}
                          </span>
                        ) : null}
                      </div>
                    );
                  })
                )}
              </div>

              <div className="game-tile-footer">
                <span className={`status-dot ${game.status}`}>{game.status}</span>
                <span className="game-tile-moves">{game.moveCount}/37 moves</span>
              </div>
            </article>
          ))}
        </section>

        {/* Telemetry */}
        <aside className="panel telemetry-panel">
          <div className="metric wide">
            <span className="metric-label">Games completed</span>
            <span className="metric-value">{gamesCompleted}/{totalGames}</span>
          </div>
          <div className="metric">
            <span className="metric-label">Active games</span>
            <span className="metric-value">{activeGames}</span>
          </div>
          <div className="metric">
            <span className="metric-label">Sockets</span>
            <span className="metric-value">{sockets}</span>
          </div>
          <div className="metric">
            <span className="metric-label">Moves measured</span>
            <span className="metric-value">{simMoves.toLocaleString()}</span>
          </div>
          <div className="metric">
            <span className="metric-label">p50</span>
            <span className="metric-value">{p50.toFixed(2)}ms</span>
          </div>
          <div className="metric">
            <span className="metric-label">p95</span>
            <span className="metric-value">{p95.toFixed(2)}ms</span>
          </div>
          <div className="metric accent">
            <span className="metric-label">p99</span>
            <span className="metric-value">{p99.toFixed(2)}ms</span>
          </div>
        </aside>
      </div>

      {/* Event console */}
      <section className="event-console">
        <div className="console-header">
          <span className="console-title">Security &amp; server events</span>
          <span className={`console-status ${running ? "streaming" : "ready"}`}>
            {running ? "● streaming" : "ready"}
          </span>
        </div>
        <div className="event-list">
          {events.map((ev) => (
            <div className={`event-row ${ev.tone}`} key={ev.id}>
              <time className="event-time">{ev.time}</time>
              <span className="event-text">{ev.text}</span>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
