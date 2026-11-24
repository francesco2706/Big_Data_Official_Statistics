/*
  SCRIPT 2 - Download di Google Trends dalla console del browser
  regione per regione: await scarica({ regioni: ["ITC1"] })
  tutto: await scarica()
*/

var REP = "rep1";
var TIME = "2011-01-01 2025-12-31";
var PAUSA_MS = [7000, 13000]; // pausa casuale
var HL = "it", TZ = -60;

var GEOS = { IT: "domestico", DE: "estero", US: "estero", FR: "estero", GB: "estero", ES: "estero" };
var CATS = { 179: "hotel", 203: "voli", 208: "attrazioni" };   // Viaggi > Hotel e alloggi, Viaggi aerei, Destinazioni turistiche

// 5 argomenti per regione, scaricati nella STESSA richiesta (sommabili)
// Il primo e' la regione; gli altri sono le mete dove si concentra il turismo.
var REGIONI = {
  ITC1: ["Piemonte", "Torino", "Lago Maggiore", "Langhe", "Sestriere"],
  ITC2: ["Valle d'Aosta", "Courmayeur", "Breuil-Cervinia", "Monte Bianco", "Aosta"],
  ITC3: ["Liguria", "Cinque Terre", "Genova", "Portofino", "Sanremo"],
  ITC4: ["Lombardia", "Milano", "Lago di Como", "Sirmione", "Livigno"],
  ITDA: ["Alto Adige", "Trentino", "Dolomiti", "Val Gardena", "Merano"],
  ITD3: ["Veneto", "Venezia", "Lago di Garda", "Verona", "Jesolo"],
  ITD4: ["Friuli-Venezia Giulia", "Trieste", "Lignano Sabbiadoro", "Grado", "Udine"],
  ITD5: ["Emilia-Romagna", "Rimini", "Bologna", "Riccione", "Ravenna"],
  ITE1: ["Toscana", "Firenze", "Pisa", "Siena", "Isola d'Elba"],
  ITE2: ["Umbria", "Perugia", "Assisi", "Orvieto", "Lago Trasimeno"],
  ITE3: ["Marche", "Urbino", "Ancona", "San Benedetto del Tronto", "Senigallia"],
  ITE4: ["Lazio", "Roma", "Città del Vaticano", "Colosseo"],
  ITF1: ["Abruzzo", "Pescara", "L'Aquila", "Gran Sasso", "Roccaraso"],
  ITF2: ["Molise", "Campobasso", "Termoli", "Isernia"],
  ITF3: ["Campania", "Napoli", "Costiera amalfitana", "Sorrento", "Ischia"],
  ITF4: ["Puglia", "Salento", "Bari", "Gargano", "Alberobello"],
  ITF5: ["Basilicata", "Matera", "Maratea"],
  ITF6: ["Calabria", "Tropea", "Reggio Calabria", "Scalea"],
  ITG1: ["Sicilia", "Palermo", "Taormina", "Siracusa", "Isole Eolie"],
  ITG2: ["Sardegna", "Costa Smeralda", "Cagliari", "Alghero", "Villasimius"],
};

// Correzioni manuali
var OVERRIDE = {   // correzioni decise dopo il controllo della tabella di risolvi()
  "Marche": "/m/01rxw2", "Lazio": "/m/04q_g", "Città del Vaticano": "/m/07ytt",
  "Molise": "/m/0kpg4", "Puglia": "/m/0c663", "Salento": "/m/03w97w", "Calabria": "/m/0c61p",
  "Cinque Terre": "/m/036vk5", "Sicilia": "/m/06w92", "Ischia": "/m/02002y",
  "Gargano": "/m/07f69d", "Gran Sasso": "/m/03f3kk",
  "Sirmione": "/m/04d2_3", "Merano": "/m/045fm9", "Riccione": "/m/090hnd"
};

// parole nel tipo di argomento che indicano un luogo / che indicano qualcos'altro (squadre, film, vini, ...)
var BUONI = ["regione", "region", "città", "city", "comune", "capoluogo", "capitale", "capital", "lago", "lake", "isola", "island",
  "arcipelago", "archipelago", "costa", "coast", "riviera", "monte", "mountain", "montagna", "catena", "massiccio", "valle", "valley",
  "zona", "area", "provincia", "province", "penisola", "peninsula", "località", "frazione", "stato", "state", "anfiteatro",
  "amphitheat", "monumento", "parco", "park", "altopiano", "plateau", "sito", "resort", "stazione sciistica", "ski"];
var CATTIVI = ["calcio", "football", "soccer", "squadra", "club", "società sportiva", "film", "serie", "canzone", "song", "singolo",
  "album", "band", "gruppo musicale", "vino", "wine", "giornale", "quotidiano", "rivista", "nave", "videogioco", "partito",
  "università", "university", "aeroporto", "airport", "stazione ferroviaria", "hotel", "ristorante", "basket", "pallavolo"];

var TOPICS = {};
var FATTE = new Set();
var LOG = [];

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }
function pausa() { return sleep(PAUSA_MS[0] + Math.random() * (PAUSA_MS[1] - PAUSA_MS[0])); }
function parseGoogle(txt) { return JSON.parse(txt.slice(txt.indexOf("{"))); }   // per togliere il prefisso )]}'

async function richiesta(url, metodo, tentativi = 6) {
  for (let k = 1; k <= tentativi; k++) {
    try {
      const r = await fetch(url, { method: metodo, credentials: "include" });
      if (r.status === 429) throw new Error("429 troppe richieste");
      if (!r.ok) throw new Error("HTTP " + r.status);
      return parseGoogle(await r.text());
    } catch (e) {
      const attesa = 60000 * k + Math.random() * 10000;
      console.warn(`  ${e.message}: riprovo tra ${Math.round(attesa / 1000)} s (${k}/${tentativi})`);
      await sleep(attesa);
    }
  }
  throw new Error("richiesta fallita: " + url.slice(0, 120));
}

function sceltaArgomento(nome, topics) {
  const t = topics.map(x => ({ ...x, tl: (x.type || "").toLowerCase() }));
  const puliti = t.filter(x => !CATTIVI.some(w => x.tl.includes(w)));
  const luoghi = puliti.filter(x => BUONI.some(w => x.tl.includes(w)));
  const stessoNome = l => l.find(x => (x.title || "").toLowerCase() === nome.toLowerCase());
  return stessoNome(luoghi) || luoghi[0] || stessoNome(puliti) || puliti[0] || t[0] || null;
}

async function risolvi() {
  const tab = [];
  for (const [area, nomi] of Object.entries(REGIONI)) {
    for (const nome of nomi) {
      if (OVERRIDE[nome]) {
        TOPICS[nome] = { mid: OVERRIDE[nome], title: nome, type: "(override manuale)" };
        tab.push({ area, nome, scelto: nome, tipo: "(override manuale)", mid: OVERRIDE[nome], alternative: "" });
        continue;
      }
      if (TOPICS[nome]) { tab.push({ area, nome, scelto: TOPICS[nome].title, tipo: TOPICS[nome].type, mid: TOPICS[nome].mid, alternative: TOPICS[nome].alt }); continue; }
      const url = `https://trends.google.com/trends/api/autocomplete/${encodeURIComponent(nome)}?hl=${HL}&tz=${TZ}`;
      const js = await richiesta(url, "GET");
      const topics = (js.default && js.default.topics) || [];
      const best = sceltaArgomento(nome, topics);
      const alt = topics.slice(0, 5).map(x => `${x.title} [${x.type}] ${x.mid}`).join(" | ");
      if (best) TOPICS[nome] = { mid: best.mid, title: best.title, type: best.type, alt };
      tab.push({ area, nome, scelto: best ? best.title : "NESSUNO", tipo: best ? best.type : "", mid: best ? best.mid : "", alternative: alt });
      await sleep(1500 + Math.random() * 1500);
    }
  }
  console.table(tab);
  scaricaFile("trends_topic.csv", toCSV(tab, ["area", "nome", "scelto", "tipo", "mid", "alternative"]));
  console.log("Controlla la tabella (e il file trends_topic.csv). Correzioni: OVERRIDE['Nome'] = '/m/...'; poi rilancia risolvi().");
}

async function serie(mids, geo, cat) {
  const req = { comparisonItem: mids.map(m => ({ keyword: m, geo, time: TIME })), category: cat, property: "" };
  const base = `https://trends.google.com/trends/api/explore?hl=${HL}&tz=${TZ}&req=${encodeURIComponent(JSON.stringify(req))}`;
  let ex;
  try { ex = await richiesta(base, "POST", 2); } catch (e) { ex = await richiesta(base, "GET"); }
  const w = ex.widgets.find(x => x.id === "TIMESERIES");
  if (!w) throw new Error("widget TIMESERIES non trovato");
  await sleep(1500 + Math.random() * 1500);
  const url = `https://trends.google.com/trends/api/widgetdata/multiline?hl=${HL}&tz=${TZ}` +
    `&req=${encodeURIComponent(JSON.stringify(w.request))}&token=${w.token}`;
  const js = await richiesta(url, "GET");
  return js.default.timelineData || [];
}

function mese(unixSec) {
  const d = new Date((Number(unixSec) + 43200) * 1000);   // +12h per evitare problemi di fuso orario
  return d.getUTCFullYear() + "-" + String(d.getUTCMonth() + 1).padStart(2, "0");
}

function toCSV(rows, cols) {
  const q = v => { const s = v === undefined || v === null ? "" : String(v); return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
  return [cols.join(",")].concat(rows.map(r => cols.map(c => q(r[c])).join(","))).join("\n");
}

function scaricaFile(nome, testo) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([testo], { type: "text/csv" }));
  a.download = nome; document.body.appendChild(a); a.click(); a.remove();
}

async function scarica(opz = {}) {
  const regioni = opz.regioni || Object.keys(REGIONI);
  const geos = opz.geos || Object.keys(GEOS);
  const cats = (opz.cats || Object.keys(CATS)).map(Number);
  const mancanti = regioni.flatMap(a => REGIONI[a].filter(n => !TOPICS[n]));
  if (mancanti.length) { console.error("Prima lancia risolvi(). Argomenti mancanti:", mancanti); return; }
  const cols = ["REF_AREA", "geo", "market", "cat", "intent", "rep", "ordine", "nome", "mid", "titolo", "TIME_PERIOD", "value", "hasData"];
  for (const area of regioni) {
    const chiave = area + "|" + REP + "|" + geos.join("") + "|" + cats.join("");
    if (FATTE.has(chiave)) { console.log(`${area}: gia' scaricata in questa sessione, salto`); continue; }
    const nomi = REGIONI[area], mids = nomi.map(n => TOPICS[n].mid);
    const righe = [];
    let i = 0;
    for (const geo of geos) for (const cat of cats) {
      i++;
      try {
        const td = await serie(mids, geo, cat);
        const vuota = td.length === 0 || td.every(p => !(p.hasData || []).some(Boolean));
        if (vuota) LOG.push({ area, geo, cat: CATS[cat], problema: "dati insufficienti" });
        for (const p of td) nomi.forEach((n, j) => righe.push({
          REF_AREA: area, geo, market: GEOS[geo], cat, intent: CATS[cat], rep: REP, ordine: j, nome: n, mid: mids[j],
          titolo: TOPICS[n].title, TIME_PERIOD: mese(p.time), value: (p.value || [])[j], hasData: (p.hasData || [])[j]
        }));
        const somma = td.reduce((s, p) => s + (p.value || []).reduce((a, b) => a + b, 0), 0) / Math.max(td.length, 1);
        console.log(`  ${area} [${i}/${geos.length * cats.length}] ${geo} ${CATS[cat]}: ${td.length} mesi, media somma ${somma.toFixed(1)}${vuota ? "  (dati insufficienti)" : ""}`);
      } catch (e) {
        LOG.push({ area, geo, cat: CATS[cat], problema: e.message });
        console.error(`  ${area} ${geo} ${CATS[cat]}: ${e.message}`);
      }
      await pausa();
    }
    scaricaFile(`trends_${area}_${REP}.csv`, toCSV(righe, cols));
    FATTE.add(chiave);
    console.log(`%c${area} completata: ${righe.length} righe salvate in trends_${area}_${REP}.csv`, "color:green;font-weight:bold");
  }
  if (LOG.length) { console.table(LOG); scaricaFile(`trends_log_${REP}.csv`, toCSV(LOG, ["area", "geo", "cat", "problema"])); }
  console.log("Fine.");
}

console.log("Script caricato. Passo successivo:  await risolvi()");