/* UniTrento faculty similarity network — static UI (sigma v3 + graphology, no build step).
   Reads graph.json (or graph_alt.json), served by `python -m unitn_net serve`.
   The composite score is recomputed client-side from the per-layer percentiles and the weight sliders. */
"use strict";

const I18N = {
  it: {
    title: "Embedded Researcher · UniTrento",
    matrix: "Matrice", matrix_title: "Dipartimenti a confronto", matrix_help: "Ogni casella conta le coppie di persone fra due strutture (struttura principale di ciascuno). Clic su una casella per vedere quelle coppie.", m_links: "tutti i collegamenti", m_unexplored: "inesplorate", m_bridge: "già coautori", close: "Chiudi", csv: "Scarica CSV", dept_comms: "Comunità nel dipartimento", view_stats: "collegamenti",
    view_dept: "Dipartimento", view_comm: "Comunità", view_all_dept: "Tutto l'ateneo", view_all_comm: "Tutte", comm_depts: "Dipartimenti nella comunità", outside: "fuori dalla vista",
    explore: "Esplora", pairs_none: "Nessuna coppia con questi filtri.", pairs_count: "coppie", pairs_shown: "le prime",
    lens: {
      all: ["Tutti i collegamenti", "La rete completa: i legami più forti secondo i pesi dei layer."],
      unexplored: ["Collaborazioni inesplorate", "Temi di ricerca molto vicini (≥ 90° percentile), nessuna pubblicazione insieme, nessuna struttura in comune."],
      coteach: ["Insegnano insieme, mai pubblicato insieme", "Tengono lo stesso insegnamento ma non hanno pubblicazioni in comune."],
      teach: ["Didattica affine, mai pubblicato insieme", "Didattica tra le più simili dell'ateneo (1% più alto), ma non lo stesso insegnamento, nessuna pubblicazione in comune."],
      bridge: ["Coautori di strutture diverse", "Hanno già pubblicato insieme pur non avendo strutture in comune: i ponti che esistono."],
    },
    dept_people: "persone", dept_sem: "con profilo semantico", dept_links: "Legami con altre strutture", dept_l: "collegamenti", dept_u: "inesplorati",
    shared_courses: "insegnamenti in comune", joint_pubs: "pubblicazioni insieme", similar_courses: "insegnamenti simili",
    search: "Cerca una persona, struttura o SSD… (/)", controls: "Controlli", color_by: "Colora per", community: "comunità", dept: "dipartimento",
    edge_threshold: "Soglia archi (composito ≥)", unexplored: "Solo collaborazioni inesplorate", show_isolated: "Mostra persone senza collegamenti", communities: "Comunità", structures: "Dipartimenti e centri", clear_filter: "Togli il filtro", phd_programmes: "Corsi di dottorato", struct_hint: "Clic per filtrare: chi appartiene anche ad altre strutture compare in tutte", struct_label: "Evidenzia struttura", struct_all: "Tutte le strutture", affiliations: "Altre strutture", node_size: "Dimensione nodi", edge_opacity: "Visibilità archi", weights_title: "Pesi dei layer", focus_hint: "Clic per isolare questa comunità", stat_people: "persone collegate", stat_edges: "archi", stat_comm: "comunità", use_conf: "Pesa la semantica per affidabilità", confidence: "affidabilità", confidence_help: "Quanto è affidabile l'arco semantico: cresce con il numero di abstract di entrambe le persone (formula n / (n + 5)). Vale il lato con meno abstract.", reset: "Ripristina pesi",
    legend: "Legenda", legend_search: "Filtra elenco…", courses: "Insegnamenti correnti", neighbours: "Vicini per layer", snapshot: "Dati aggiornati al", build: "build",
    back: "← Indietro", print: "Stampa", report_error: "Segnala", report_subject: "Segnalazione dati · Embedded Researcher",
    report_body: "Persona: {name} ({id})\nStruttura: {dept}\nRuolo: {role}\nSSD: {ssd}\n\nSegnalazione / correzione richiesta:\n",
    model_label: "Modello semantico", res_label: "Dettaglio comunità", res_fine: "Temi (2.0)", res_macro: "Macro-aree (1.0)", all_layers: "Tutti",
    appearance_title: "Aspetto del grafo", model_group_title: "Modello e partizione",
    theme_label: "Tema visivo", theme_light: "Chiaro", theme_dark: "Notte",
    reset_appearance: "Ripristina", reset_done: "✓ Ripristinato",
    tip_png: "Scarica un'immagine PNG ad alta risoluzione del grafo attuale (pronta per slide o report).",
    tip_share: "Copia negli appunti il link diretto alla vista corrente (dipartimento, comunità, lente o persona selezionata).",
    tip_about: "Informazioni sul progetto e crediti.",
    about_title: "Embedded Researcher · Il progetto",
    about_p1: "Questo sito è pensato per rendere navigabile ed esplorabile la rete di affinità scientifica e didattica dell'Università degli Studi di Trento: mostra chi lavora su temi vicini per pubblicazioni, insegnamenti, riferimenti bibliografici e settori disciplinari, così da far emergere collaborazioni possibili che ancora non esistono.",
    about_p2: "Per ogni collegamento sono mostrate le prove concrete (coppie di articoli con link DOI, insegnamenti in comune, colleghi ponte). Non è una classifica e non valuta la produzione individuale: le citazioni non sono usate per misurare le persone e la dimensione dei punti dipende solo dal numero di pubblicazioni.",
    about_credits_label: "Progetto",
    about_credits_sub: "Università degli Studi di Trento · Licenza Open Source GNU AGPLv3",
    panel_bridge_btn: "Trova ponte…",
    bridge_title: "Trova ponte tra due ricercatori",
    tip_bridge: "Confronta due ricercatori dell'ateneo o individua la catena più breve e forte di colleghi che li collega (A ↔ Ponte ↔ B).",
    bridge_hint: "Cerca due persone (oppure clicca due punti sul grafo mentre questo riquadro è aperto) per vedere il legame diretto o la catena di colleghi che fa da ponte.",
    bridge_placeholder_a: "Persona A (cerca o clicca sul grafo)…",
    bridge_placeholder_b: "Persona B (cerca o secondo clic)…",
    bridge_direct: "Collegamento diretto",
    bridge_path: "Percorso ponte più forte",
    bridge_none: "Nessun percorso di collegamento trovato nella rete attiva.",
    scope_all: "Tutti", scope_cross: "Altri dip.", scope_unexplored: "Inesplorati",
    tip_scope_cross: "Mostra sul grafo e nella lista solo i vicini che appartengono ad altri dipartimenti o centri.",
    tip_scope_unexplored: "Mostra sul grafo e nella lista solo le collaborazioni potenziali inesplorate di questa persona.",
    build_title: "Costruisci la rete sulla tua macchina",
    build_desc: "Per tutela della privacy, i dati grezzi e i grafi calcolati non sono inclusi nel repository Git. Puoi generarli localmente con un clic dai dati aperti UniTrento e dal catalogo IRIS.",
    build_with_alt: "Calcola anche il modello alternativo (Gemma-2)",
    build_btn: "Avvia calcolo ora (1 clic)",
    build_running: "Calcolo in corso…",
    tip_theme: "Passa manualmente tra modalità chiara e modalità notte (senza dipendere dal tema di sistema).",
    tip_reset_appearance: "Riporta colorazione, soglia archi, opacità e dimensione dei nodi ai valori predefiniti.",
    tip_stats: "Persone con almeno un collegamento nella rete, numero totale di collegamenti (archi) e numero di comunità tematiche con almeno 5 membri.",
    tip_matrix: "Apre la matrice comparativa tra tutti i dipartimenti e centri di ricerca.",
    tip_lang: "Cambia lingua dell'interfaccia (Italiano / English).",
    tip_zoom_in: "Ingrandisci il grafo.",
    tip_zoom_out: "Riduci lo zoom del grafo.",
    tip_zoom_fit: "Ricentra e adatta il grafo allo schermo.",
    tip_tab_explore: "Filtra per dipartimento o comunità e scopri le coppie di ricercatori affini.",
    tip_tab_legend: "Elenco completo delle comunità tematiche e delle strutture dell'ateneo.",
    tip_tab_controls: "Personalizza aspetto del grafo, pesi dei layer, granularità delle comunità e modello semantico.",
    tip_dept_select: "Isola sul grafo una singola struttura (dipartimento, facoltà, centro o scuola) e mostra le sue collaborazioni.",
    tip_comm_select: "Isola sul grafo una comunità tematica individuata automaticamente dall'algoritmo di Leiden.",
    tip_color_by: "Sceglie se colorare i nodi per comunità tematica (calcolata sui legami) o per dipartimento di appartenenza.",
    tip_threshold: "Mostra sul grafo solo i collegamenti il cui punteggio complessivo (media pesata dei percentili dei layer attivi) è almeno pari a questa soglia.",
    tip_edge_opacity: "Regola l'opacità delle linee di collegamento sul grafo per facilitarne la lettura.",
    tip_node_size: "Scala la dimensione dei punti sul grafo. La grandezza di base dipende solo dal numero di pubblicazioni (mai dalle citazioni).",
    tip_isolated: "Mostra o nasconde in basso le persone prive di collegamenti forti (spesso perché hanno meno di 3 abstract disponibili).",
    tip_weights: "Quanto pesa ciascun layer nel punteggio complessivo. Sposta uno slider a 0 o deseleziona la casella per escluderlo.",
    tip_reset: "Riporta tutti i pesi dei layer ai valori predefiniti.",
    tip_res_group: "Granularità dell'algoritmo di Leiden che individua i gruppi tematici nella rete.",
    tip_res_fine: "Risoluzione Leiden 2.0 (14 comunità): suddivide i dipartimenti grandi in sottogruppi tematici specifici (es. idraulica vs strutture, fisica quantistica vs materiali) e fa emergere gruppi trasversali.",
    tip_res_macro: "Risoluzione Leiden 1.0 (10 macro-aree): raggruppamento più ampio che ricalca da vicino i confini dei dipartimenti.",
    tip_model_group: "Modello di intelligenza artificiale (embedding) che trasforma titoli e abstract in vettori numerici per misurare l'affinità di argomento.",
    tip_model_qwen: "Qwen3-Embedding-0.6B (modello principale): ottiene la migliore capacità predittiva di future collaborazioni sui dati di ateneo (AUC-PR 0,045).",
    tip_model_gemma: "Google EmbeddingGemma-2 (modello alternativo): secondo modello multilingue usato per confrontare e verificare la robustezza dei legami semantici.",
    tip_pct: "Percentile (0–100°): indica che questa coppia è più affine di tale percentuale di tutte le coppie dell'ateneo su questo layer.",
    tip_cos: "Similarità del coseno (0–1) tra i vettori dei due testi: più è vicino a 1, più i due abstract o programmi d'esame trattano lo stesso argomento.",
    tip_ssd: "Settore Scientifico-Disciplinare (SSD) ministeriale di inquadramento.",
    tip_unexplored: "Collaborazione potenziale: affinità tematica nel 10% più alto (≥ 90° percentile), nessuna pubblicazione insieme e nessuna struttura in comune.",
    tip_print: "Stampa o salva in PDF la scheda corrente.",
    tip_report: "Invia una segnalazione via email per correggere dati o afferenze.",
    intro: "Ogni punto è una persona; la dimensione cresce con il numero di pubblicazioni (mai con le citazioni). " +
           "Clicca una persona per vedere a chi è vicina e perché. " +
           "Scegli un dipartimento o una comunità per isolarlo; usa le viste qui sopra per esplorare i legami.",
    layers: { sem: "Semantica", coupling: "Accoppiamento bibliografico", direct: "Citazioni dirette", coauth: "Coautorialità", teach: "Didattica", field: "Settore (SSD)" },
    layers_short: { sem: "Semantica", coupling: "Bibliografia", direct: "Citazioni", coauth: "Coautori", teach: "Didattica", field: "Settore" },
    layer_help: {
      sem: "Similarità tra i testi (titolo + abstract intero) delle pubblicazioni, escluse quelle in comune; chi ha meno di 3 abstract nella stessa lingua non ha questo layer. Il punteggio è calibrato: quanto la somiglianza è insolita rispetto a coppie casuali di abstract della stessa lingua (non è un coseno); le prove mostrano il coseno vero.",
      coupling: "Riferimenti bibliografici condivisi (OpenAlex), escluse le pubblicazioni in comune",
      direct: "Citazioni reciproche tra i lavori dei due docenti (OpenAlex)",
      coauth: "Numero di pubblicazioni firmate insieme",
      teach: "Insegnamenti tenuti insieme, corsi di studio in comune e similarità tra le descrizioni degli insegnamenti",
      field: "Stesso SSD = 1, stessa area CUN = 0.5",
    },
    no_data: "n.d.", role: "Ruolo", ssd: "SSD", pubs: "pubblicazioni", shared_programmes: "corsi di studio condivisi",
    none: "nessuno", isolated: "senza collegamenti (dati insufficienti)", cites: "cita", weight: "peso", unexplored_tag: "inesplorata", community_label: "Comunità",
    loading: "Caricamento…", load_error: "Impossibile caricare graph.json: eseguire la pipeline fino a `export` e avviare `python -m unitn_net serve`.",
  },
  en: {
    title: "Embedded Researcher · UniTrento",
    matrix: "Matrix", matrix_title: "Departments compared", matrix_help: "Each cell counts the pairs of people between two structures (primary structure of each). Click a cell to see those pairs.", m_links: "all links", m_unexplored: "unexplored", m_bridge: "already co-authors", close: "Close", csv: "Download CSV", dept_comms: "Communities in the department", view_stats: "links",
    view_dept: "Department", view_comm: "Community", view_all_dept: "Whole university", view_all_comm: "All", comm_depts: "Departments in the community", outside: "outside the view",
    explore: "Explore", pairs_none: "No pairs with these filters.", pairs_count: "pairs", pairs_shown: "top",
    lens: {
      all: ["All links", "The whole network: the strongest ties under the layer weights."],
      unexplored: ["Unexplored collaborations", "Very close research topics (≥ 90th percentile), no joint publication, no structure in common."],
      coteach: ["Teach together, never published together", "They teach the same course but have no joint publication."],
      teach: ["Similar teaching, never published together", "Teaching among the most similar in the university (top 1%), but not the same course, no joint publication."],
      bridge: ["Co-authors across structures", "They already published together without sharing a structure: the bridges that exist."],
    },
    dept_people: "people", dept_sem: "with a semantic profile", dept_links: "Links with other structures", dept_l: "links", dept_u: "unexplored",
    shared_courses: "courses in common", joint_pubs: "joint publications", similar_courses: "similar courses",
    search: "Search a person, department or SSD… (/)", controls: "Controls", color_by: "Colour by", community: "community", dept: "department",
    edge_threshold: "Edge threshold (composite ≥)", unexplored: "Unexplored collaborations only", show_isolated: "Show people without links", communities: "Communities", structures: "Departments and centres", clear_filter: "Clear filter", phd_programmes: "Doctoral programmes", struct_hint: "Click to filter: people in several structures show up in each", struct_label: "Highlight structure", struct_all: "All structures", affiliations: "Other structures", node_size: "Node size", edge_opacity: "Edge visibility", weights_title: "Layer weights", focus_hint: "Click to isolate this community", stat_people: "linked people", stat_edges: "edges", stat_comm: "communities", use_conf: "Weight semantics by confidence", confidence: "confidence", confidence_help: "How reliable the semantic edge is: it grows with the number of abstracts of both people (formula n / (n + 5)). The weaker side counts.", reset: "Reset weights",
    legend: "Legend", legend_search: "Filter list…", courses: "Current courses", neighbours: "Neighbours by layer", snapshot: "Data snapshot", build: "build",
    back: "← Back", print: "Print", report_error: "Report", report_subject: "Data report · Embedded Researcher",
    report_body: "Person: {name} ({id})\nStructure: {dept}\nRole: {role}\nSSD: {ssd}\n\nIssue / correction requested:\n",
    model_label: "Semantic model", res_label: "Community detail", res_fine: "Themes (2.0)", res_macro: "Macro-areas (1.0)", all_layers: "All",
    appearance_title: "Graph appearance", model_group_title: "Model & partition",
    theme_label: "Appearance theme", theme_light: "Light", theme_dark: "Dark",
    reset_appearance: "Reset", reset_done: "✓ Reset",
    tip_png: "Download a high-resolution PNG image of the current graph (ready for slides or reports).",
    tip_share: "Copy a direct link to the current view (selected department, community, lens, or person) to the clipboard.",
    tip_about: "About the project and credits.",
    about_title: "Embedded Researcher · About the project",
    about_p1: "This site is designed to make the research and teaching affinity network of the University of Trento navigable and explorable: it shows who works on related topics across publications, courses, bibliographic references, and academic fields, bringing to light potential collaborations that do not yet exist.",
    about_p2: "Every connection is backed by concrete evidence (pairs of papers with DOI links, shared courses, bridging colleagues). It is not a ranking and does not evaluate individual performance: citations are never used to score people, and node size depends solely on publication count.",
    about_credits_label: "Project",
    about_credits_sub: "University of Trento (Università degli Studi di Trento) · GNU AGPLv3 Open Source License",
    panel_bridge_btn: "Find bridge…",
    bridge_title: "Find bridge between two researchers",
    tip_bridge: "Compare two researchers or find the shortest and strongest chain of colleagues connecting them (A ↔ Bridge ↔ B).",
    bridge_hint: "Search two people (or click two dots on the graph while this box is open) to see their direct link or the chain of bridging colleagues.",
    bridge_placeholder_a: "Person A (search or click on graph)…",
    bridge_placeholder_b: "Person B (search or second click)…",
    bridge_direct: "Direct link",
    bridge_path: "Strongest bridge path",
    bridge_none: "No connecting path found in the active network.",
    scope_all: "All", scope_cross: "Other depts", scope_unexplored: "Unexplored",
    tip_scope_cross: "Show on the graph and in the list only neighbours belonging to other departments or centres.",
    tip_scope_unexplored: "Show on the graph and in the list only this person's unexplored potential collaborations.",
    build_title: "Build the network on your machine",
    build_desc: "To protect privacy, raw data and computed graphs are not stored in Git. You can build them locally in one click from UniTrento open data and IRIS.",
    build_with_alt: "Also compute the alternative model (Gemma-2)",
    build_btn: "Start build now (1 click)",
    build_running: "Building pipeline…",
    tip_theme: "Manually switch between light and dark mode (independent of OS theme).",
    tip_reset_appearance: "Restore node colouring, edge threshold, opacity, and node size to default values.",
    tip_stats: "People with at least one link in the network, total number of edges, and thematic communities with at least 5 members.",
    tip_matrix: "Open the comparison matrix across all departments and research centres.",
    tip_lang: "Switch interface language (Italiano / English).",
    tip_zoom_in: "Zoom in.",
    tip_zoom_out: "Zoom out.",
    tip_zoom_fit: "Reset and fit the graph to the screen.",
    tip_tab_explore: "Filter by department or community and discover pairs of researchers working on close topics.",
    tip_tab_legend: "Full searchable list of thematic communities and university structures.",
    tip_tab_controls: "Customise graph appearance, layer weights, community resolution, and embedding model.",
    tip_dept_select: "Isolate a single structure (department, faculty, centre, or school) and inspect its connections.",
    tip_comm_select: "Isolate a thematic community automatically detected by the Leiden algorithm.",
    tip_color_by: "Colour nodes either by thematic community (detected from links) or by primary department.",
    tip_threshold: "Only display edges whose composite score (weighted mean of active layer percentiles) meets this threshold.",
    tip_edge_opacity: "Adjust the opacity of connection lines on the graph.",
    tip_node_size: "Scale node size. Base size depends only on publication count (never on citations).",
    tip_isolated: "Show or hide people without strong links (usually because fewer than 3 abstracts are available).",
    tip_weights: "How much each layer contributes to the composite score. Drag to 0 or uncheck to disable a layer.",
    tip_reset: "Restore all layer weights to their default values.",
    tip_res_group: "Resolution parameter of the Leiden community detection algorithm.",
    tip_res_fine: "Leiden resolution 2.0 (14 communities): splits large departments into specific thematic groups (e.g. hydrology vs structures, quantum physics vs materials) and reveals cross-department clusters.",
    tip_res_macro: "Leiden resolution 1.0 (10 macro-areas): broader grouping that closely follows departmental boundaries.",
    tip_model_group: "AI embedding model used to turn publication titles and abstracts into numerical vectors.",
    tip_model_qwen: "Qwen3-Embedding-0.6B (primary model): achieves the highest predictive accuracy for future co-authorships on university data (AUC-PR 0.045).",
    tip_model_gemma: "Google EmbeddingGemma-2 (comparison model): alternative multilingual model used to verify the robustness of semantic links.",
    tip_pct: "Percentile (0–100th): this pair is closer than this percentage of all pairs in the university on this layer.",
    tip_cos: "Cosine similarity (0–1) between the two text vectors: closer to 1 means the two abstracts or course syllabi cover the same topic.",
    tip_ssd: "Italian ministerial academic discipline code (Settore Scientifico-Disciplinare).",
    tip_unexplored: "Potential collaboration: semantic affinity in the top 10% (≥ 90th percentile), no joint publications, and no shared structure.",
    tip_print: "Print or save the current sheet as PDF.",
    tip_report: "Send an email report to request a data or affiliation correction.",
    intro: "Each dot is a person; size grows with the number of publications (never with citations). " +
           "Click a person to see who they are close to and why. " +
           "Pick a department or a community to isolate it; use the views above to explore connections.",
    layers: { sem: "Semantic", coupling: "Bibliographic coupling", direct: "Direct citations", coauth: "Co-authorship", teach: "Teaching", field: "Field (SSD)" },
    layers_short: { sem: "Semantic", coupling: "Coupling", direct: "Citations", coauth: "Co-authors", teach: "Teaching", field: "Field" },
    layer_help: {
      sem: "Similarity between publication texts (title + whole abstract), joint papers excluded; people with fewer than 3 abstracts in one language do not have this layer. The score is calibrated: how unusual the similarity is compared with random pairs of abstracts in the same language (not a cosine); the evidence shows the real cosine.",
      coupling: "Shared references (OpenAlex), joint papers excluded",
      direct: "Citations between the two people's works (OpenAlex)",
      coauth: "Number of joint publications",
      teach: "Courses taught together, degree programmes in common and similarity between course descriptions",
      field: "Same SSD = 1, same CUN area = 0.5",
    },
    no_data: "n/a", role: "Role", ssd: "SSD", pubs: "publications", shared_programmes: "shared degree programmes",
    none: "none", isolated: "without links (insufficient data)", cites: "cites", weight: "weight", unexplored_tag: "unexplored", community_label: "Community",
    loading: "Loading…", load_error: "Cannot load graph.json: run the pipeline up to `export` and start `python -m unitn_net serve`.",
  },
};

const G = window.graphology;
const UndirectedGraph = G.UndirectedGraph || (G.default && G.default.UndirectedGraph) || G.Graph || G;
const SigmaClass = window.Sigma.Sigma || window.Sigma.default || window.Sigma;

const initialTheme = (() => {
  try {
    const saved = localStorage.getItem("theme");
    if (saved === "dark" || saved === "light") return saved;
  } catch {}
  return (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) ? "dark" : "light";
})();

const state = {
  lang: (() => { try { return localStorage.getItem("lang") || "it"; } catch { return "it"; } })(),
  theme: initialTheme,
  weights: {}, defaultWeights: {}, enabled: {},
  threshold: initialTheme === "dark" ? 0.62 : 0.55,
  defaultThreshold: initialTheme === "dark" ? 0.62 : 0.55,
  nodeScale: 1,
  edgeAlpha: initialTheme === "dark" ? 0.24 : 0.38,
  defaultEdgeAlpha: initialTheme === "dark" ? 0.24 : 0.38,
  userModifiedEdgeAlpha: false,
  lens: "all", useConf: false, showIsolated: false, focus: null, structFocus: "", structWith: "",
  hoverNode: null, hoverT: 0, hoverTarget: 0, hoverRaf: 0, colorBy: "community", selected: null,
  hoverPair: null, hoveredEdge: null,
  bridgeA: null, bridgeB: null, bridgePath: null, bridgeEdges: null,
  tab: "explore", legendMode: "communities", legendQuery: "", panelLayer: "all", panelScope: "all",
  modelTag: "default", resolution: "2.0",
  data: null, graph: null, renderer: null,
};

const t = (k) => I18N[state.lang][k];
const esc = (v) => String(v == null ? "" : v).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const layersShown = () => state.data.meta.layers.filter((l) => state.hasLayer[l]);
const isUnit = (name) => /^(Dipartimento|Facoltà|Centro|Scuola)/.test(name);
const shortUnit = (name) => (name || "").replace(/^Dipartimento di |^Facoltà di |^Centro (Interdipartimentale )?(di )?|^Scuola di /, "");
const noCoauth = (a) => !(a.raw.coauth > 0);
const LENSES = ["all", "unexplored", "coteach", "teach", "bridge"];

function lensMatch(a) {
  switch (state.lens) {
    case "unexplored": return a.unexplored;
    case "coteach": return a.coTeach && noCoauth(a);
    case "teach": return !a.coTeach && noCoauth(a) && (a.p.teach || 0) >= 0.99;
    case "bridge": return a.raw.coauth > 0 && a.cross;
    default: return true;
  }
}

const PALETTE = ["#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f", "#edc948", "#b07aa1", "#ff9da7", "#9c755f", "#86bcb6", "#d37295", "#499894"];
const ISOLATED_COLOR = "#aab1bd";
const MIN_COMMUNITY = 5;
let DARK = state.theme === "dark";
let EDGE_RGB = DARK ? [125, 145, 185] : [100, 110, 130];
let DIM_HEX = DARK ? "#4a5060" : "#8e95a3";
let HIGHLIGHT = DARK ? "#2997ff" : "#0071e3";
let LENS_EDGE = DARK ? "#ffb340" : "#d97706";
let EDGE_COLOR = `rgba(${EDGE_RGB.join(",")},0.2)`;
let BG_HEX = DARK ? "#000000" : "#f5f5f7";
const rgba2 = (rgb, a) => `rgba(${rgb.join(",")},${Math.min(a, 0.95).toFixed(3)})`;
const REDUCED = !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);

function applyTheme(theme, persist = true) {
  state.theme = theme === "dark" ? "dark" : "light";
  DARK = state.theme === "dark";
  document.documentElement.dataset.theme = state.theme;
  if (persist) {
    try { localStorage.setItem("theme", state.theme); } catch {}
  }
  EDGE_RGB = DARK ? [125, 145, 185] : [100, 110, 130];
  DIM_HEX = DARK ? "#4a5060" : "#8e95a3";
  HIGHLIGHT = DARK ? "#2997ff" : "#0071e3";
  LENS_EDGE = DARK ? "#ffb340" : "#d97706";
  EDGE_COLOR = `rgba(${EDGE_RGB.join(",")},0.2)`;
  BG_HEX = DARK ? "#000000" : "#f5f5f7";
  state.defaultEdgeAlpha = DARK ? 0.24 : 0.38;
  if (!state.userModifiedEdgeAlpha) {
    state.edgeAlpha = state.defaultEdgeAlpha;
    const eoEl = document.getElementById("edge-opacity"), eoOut = document.getElementById("edge-opacity-out");
    if (eoEl) eoEl.value = state.edgeAlpha;
    if (eoOut) eoOut.textContent = state.edgeAlpha.toFixed(2);
  }
  const moon = document.getElementById("theme-icon-moon"), sun = document.getElementById("theme-icon-sun");
  if (moon) moon.hidden = DARK;
  if (sun) sun.hidden = !DARK;
  document.querySelectorAll("#theme-switch button").forEach((b) => b.classList.toggle("on", b.dataset.themeVal === state.theme));
  if (state.renderer) {
    if (state.renderer.setSetting) {
      state.renderer.setSetting("labelColor", { color: DARK ? "#f5f5f7" : "#1d1d1f" });
      state.renderer.setSetting("defaultEdgeColor", EDGE_COLOR);
    }
    state.renderer.refresh();
  }
  const mat = document.getElementById("matrix");
  if (mat && !mat.hidden && state.graph) openMatrix();
}

const rgbaMix = (hex, k, a) => {
  const n = parseInt(hex.slice(1), 16), b = parseInt(BG_HEX.slice(1), 16);
  const m = (s) => Math.round(((n >> s) & 255) * (1 - k) + ((b >> s) & 255) * k);
  return `rgba(${m(16)},${m(8)},${m(0)},${a.toFixed(3)})`;
};
const rgba = (hex, a) => { const n = parseInt(hex.slice(1), 16); return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`; };

function communityRank() {
  if (!state._rank) {
    const real = state.data.communities.filter((c) => c.size >= MIN_COMMUNITY).sort((a, b) => b.size - a.size);
    state._rank = new Map(real.map((c, i) => [c.id, i]));
  }
  return state._rank;
}

// Disambiguate communities that share the same dominant department name (e.g. DICAM hydrology vs structures).
function commTitle(c) {
  const base = c.name || `${t("community_label")} ${c.id}`;
  const real = state.data.communities.filter((x) => x.size >= MIN_COMMUNITY && x.name === c.name);
  if (real.length > 1 && c.label) {
    const top2 = c.label.split(", ").slice(0, 2).join(", ");
    return `${base} (${top2})`;
  }
  return base;
}

const inStruct = (n) => !state.structFocus || (n.affiliations || []).includes(state.structFocus);
const isIsolated = (n) => !communityRank().has(n.community);
function communityColor(id) {
  const r = communityRank().get(id);
  return r === undefined ? ISOLATED_COLOR : r < PALETTE.length ? PALETTE[r] : color(r);
}

function color(i) {
  const h = (i * 137.508) % 360, s = 0.6, l = 0.48, a = s * Math.min(l, 1 - l);
  const f = (n) => { const k = (n + h / 30) % 12; return Math.round(255 * (l - a * Math.max(-1, Math.min(k - 3, 9 - k, 1)))).toString(16).padStart(2, "0"); };
  return `#${f(0)}${f(8)}${f(4)}`;
}

function setTab(tab) {
  state.tab = tab;
  document.querySelectorAll("#side-tabs button").forEach((b) => b.classList.toggle("on", b.dataset.tab === tab));
  const showTabs = !state.selected;
  document.getElementById("side-nav").hidden = !showTabs;
  document.getElementById("tab-explore").hidden = !showTabs || tab !== "explore";
  document.getElementById("tab-legend").hidden = !showTabs || tab !== "legend";
  document.getElementById("tab-controls").hidden = !showTabs || tab !== "controls";
  document.getElementById("panel").hidden = !!showTabs;
}

function updateStatsText() {
  if (!state.data) return;
  const isoCount = state.data.nodes.filter(isIsolated).length;
  const realCount = state.data.communities.filter((c) => c.size >= MIN_COMMUNITY).length;
  state.statsText = `${state.data.nodes.length - isoCount} ${t("stat_people")} · ${state.data.edges.length} ${t("stat_edges")} · ${realCount} ${t("stat_comm")}`;
  if (!state.view) document.getElementById("stats").textContent = state.statsText;
}

function syncColorByButtons() {
  document.querySelectorAll("#color-by button").forEach((b) => b.classList.toggle("on", b.dataset.value === state.colorBy));
  if (state.graph) {
    state.graph.forEachNode((id, a) => {
      state.graph.setNodeAttribute(id, "color", nodeColor(a));
    });
  }
}

function flashButton(btn) {
  if (!btn) return;
  if (btn._flashTimer) clearTimeout(btn._flashTimer);
  btn.classList.add("flash-ok");
  btn.textContent = t("reset_done");
  btn._flashTimer = setTimeout(() => {
    btn.classList.remove("flash-ok");
    if (btn.dataset.i18n) btn.textContent = t(btn.dataset.i18n);
    btn._flashTimer = 0;
  }, 900);
}

function applyI18n() {
  document.documentElement.lang = state.lang;
  document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => { el.placeholder = t(el.dataset.i18nPlaceholder); });
  document.querySelectorAll("[data-i18n-tip]").forEach((el) => { el.dataset.tip = t(el.dataset.i18nTip) || ""; });
  document.getElementById("lang").textContent = state.lang === "it" ? "EN" : "IT";
  document.title = t("title");
  if (!state.data) return;
  updateStatsText();
  buildWeights();
  buildLegend();
  buildLenses();
  buildExplore();
  if (state.bridgeA || state.bridgeB) renderBridge();
  if (state.selected) showPanel(state.selected);
  const ab = document.getElementById("about");
  if (ab && !ab.hidden) openAbout();
}

function composite(p, conf) {
  let num = 0, den = 0;
  for (const l of state.data.meta.layers) {
    if (!state.enabled[l] || p[l] === undefined) continue;
    const w = state.weights[l] * (state.useConf && conf && conf[l] !== undefined ? conf[l] : 1);
    num += w * p[l];
    den += w;
  }
  return den > 0 ? num / den : null;
}

function recompute(fromUser = false) {
  const g = state.graph;
  if (!g) return;
  g.forEachEdge((e, a) => { g.setEdgeAttribute(e, "w", composite(a.p, a.conf)); });
  if (fromUser && (state.bridgeA || state.bridgeB)) setBridgePair(state.bridgeA, state.bridgeB);
  if (fromUser && state.view && !state.selected) {
    applyFocus(false);
  } else if (state.renderer) {
    state.renderer.refresh();
  }
}

function buildWeights() {
  const box = document.getElementById("weights");
  box.innerHTML = "";
  for (const l of layersShown()) {
    const isOn = !!state.enabled[l] && state.weights[l] > 0;
    const row = document.createElement("div");
    row.className = "weight" + (isOn ? "" : " off");
    row.dataset.tip = t("layer_help")[l];
    row.innerHTML = `<label class="weight-head"><input type="checkbox" ${isOn ? "checked" : ""}><span class="name">${t("layers")[l]}</span><output>${Number(state.weights[l]).toFixed(2)}</output></label>` +
      `<input type="range" min="0" max="1" step="0.05" value="${state.weights[l]}">`;
    const head = row.firstElementChild, [cb, , out] = head.children, range = row.lastElementChild;
    cb.onchange = () => {
      state.enabled[l] = cb.checked;
      if (cb.checked && state.weights[l] === 0) {
        state.weights[l] = state.defaultWeights[l] || 0.10;
        range.value = state.weights[l];
        out.textContent = state.weights[l].toFixed(2);
      }
      row.classList.toggle("off", !cb.checked || state.weights[l] === 0);
      recompute(true);
    };
    range.oninput = () => {
      const v = +range.value;
      state.weights[l] = v;
      out.textContent = v.toFixed(2);
      state.enabled[l] = v > 0;
      cb.checked = v > 0;
      row.classList.toggle("off", v === 0);
      recompute(true);
    };
    box.appendChild(row);
  }
}

function structColor(name) {
  const i = state.structIndex ? state.structIndex.get(name) : undefined;
  return i === undefined ? ISOLATED_COLOR : i < PALETTE.length ? PALETTE[i] : color(i);
}

function setStruct(name, withName) {
  state.structFocus = name || "";
  state.structWith = (name && withName) || "";
  if (state.structFocus) state.focus = null;
  buildLegend();
  buildExplore();
  applyFocus();
}

function setFocus(id) {
  state.focus = id === null || id === undefined || id === "" ? null : +id;
  if (state.focus !== null) {
    state.structFocus = "";
    state.structWith = "";
  }
  buildLegend();
  buildExplore();
  applyFocus();
}

// Switch between resolution partitions stored in meta.partitions (e.g. "2.0" vs "1.0")
function applyResolution(resKey, resetCam = true) {
  const parts = (state.data && state.data.meta && state.data.meta.partitions) || {};
  const p = parts[resKey];
  if (!p) return;
  state.resolution = resKey;
  state.focus = null;
  state.colorBy = "community";
  state.data.communities = p.communities;
  state._rank = null;
  for (const n of state.data.nodes) {
    if (p.membership[n.id] !== undefined) n.community = p.membership[n.id];
  }
  if (state.graph) {
    state.graph.forEachNode((id, a) => {
      const cid = p.membership[id] !== undefined ? p.membership[id] : a.community;
      state.graph.mergeNodeAttributes(id, { community: cid, color: nodeColor({ ...a, community: cid }) });
    });
  }
  syncColorByButtons();
  updateStatsText();
  document.querySelectorAll("#res-switch button").forEach((b) => b.classList.toggle("on", b.dataset.res === resKey));
  buildLegend();
  buildExplore();
  applyFocus(resetCam);
}

// Switch between default (Qwen3) and alt (EmbeddingGemma-2) graph files
function switchModel(tag) {
  if (tag === state.modelTag) return;
  const file = tag === "alt" ? "graph_alt.json" : "graph.json";
  const loading = document.getElementById("loading");
  loading.classList.remove("done");
  fetch(file)
    .then((r) => { if (!r.ok) throw new Error(r.statusText); return r.json(); })
    .then((data) => {
      state.modelTag = tag;
      document.querySelectorAll("#model-switch button").forEach((b) => b.classList.toggle("on", b.dataset.model === tag));
      const prevSel = state.selected, prevDept = state.structFocus, prevComm = state.focus, prevLens = state.lens, prevRes = state.resolution;
      const savedWeights = { ...state.weights }, savedEnabled = { ...state.enabled };
      if (state.renderer) { state.renderer.kill(); state.renderer = null; }
      init(data, true);
      for (const l of data.meta.layers) {
        if (savedWeights[l] !== undefined) state.weights[l] = savedWeights[l];
        if (savedEnabled[l] !== undefined) state.enabled[l] = savedEnabled[l];
      }
      buildWeights();
      recompute();
      if (prevRes && data.meta.partitions && data.meta.partitions[prevRes]) applyResolution(prevRes, false);
      if (prevLens !== "all") setLens(prevLens);
      if (prevDept && state.structIndex.has(prevDept)) setStruct(prevDept);
      else if (prevComm !== null && state.data.communities.some((c) => c.id === prevComm)) setFocus(prevComm);
      if (prevSel && state.graph.hasNode(prevSel)) select(prevSel);
      loading.classList.add("done");
    })
    .catch((err) => {
      loading.classList.add("done");
      alert(err.message);
    });
}

const inFocus = (a) => (!state.structFocus || inStruct(a)) && (state.focus === null || a.community === state.focus);
const neighborMatchesScope = (a) => state.panelScope === "cross" ? !!a.cross : state.panelScope === "unexplored" ? !!a.unexplored : true;

function applyFocus(resetCam = true) {
  const g = state.graph, r = state.renderer;
  g.forEachNode((k, a) => { if (a.x !== a.ox || a.y !== a.oy) g.mergeNodeAttributes(k, { x: a.ox, y: a.oy }); });
  state.view = null;
  const single = !!state.structFocus || state.focus !== null, lens = state.lens !== "all";
  let nLinks = 0;
  if (state.selected) {
    const me = state.selected, members = new Set([me]), E = [];
    g.forEachEdge(me, (e, a, s, tg) => {
      if (!neighborMatchesScope(a)) return;
      members.add(s === me ? tg : s);
    });
    g.forEachEdge((e, a, s, tg) => {
      if (members.has(s) && members.has(tg)) {
        if ((s === me || tg === me) && !neighborMatchesScope(a)) return;
        E.push([s, tg, s === me || tg === me ? 0.5 : 0.15]);
        if (s === me || tg === me) nLinks++;
      }
    });
    state.view = { members, partners: new Set(), single: true, ego: me, n: members.size };
    const box = layoutLocal([...members], E);
    if (r.setCustomBBox && box) r.setCustomBBox(box);
  } else if (single || lens) {
    const inside = new Set(), members = new Set(), partners = new Set(), E = [];
    if (single) g.forEachNode((k, a) => { if (inFocus(a)) inside.add(k); });
    g.forEachEdge((e, a, s, tg) => {
      if (a.w === null || !passesFilters(s, tg) || (lens && !lensMatch(a))) return;
      E.push([s, tg, lens ? 0.6 : a.w]);
      for (const k of [s, tg]) (!single || inside.has(k) ? members : partners).add(k);
    });
    if (!lens) inside.forEach((k) => members.add(k));
    nLinks = E.length;
    state.view = { members, partners, single, n: members.size + partners.size };
    if (single) {
      const box = layoutLocal([...members, ...partners], E);
      if (r.setCustomBBox && box) r.setCustomBBox(box);
    } else if (state.fitBox) state.fitBox();
  } else if (state.fitBox) state.fitBox();
  if (r.setSetting) r.setSetting("labelRenderedSizeThreshold", state.view && state.view.single ? 5 : 11);
  document.getElementById("stats").textContent = state.view ? `${state.view.members.size - (state.view.ego ? 1 : 0)} ${t("dept_people")} · ${nLinks} ${t("view_stats")}` : state.statsText;
  document.getElementById("intro").hidden = !!state.view || !!state.selected;
  writeHash();
  if (resetCam) r.getCamera().animatedReset({ duration: 350 });
  r.refresh();
}

function layoutLocal(nodes, E) {
  const g = state.graph;
  if (!nodes.length) return null;
  const linked = new Set(); for (const [s, tg] of E) { linked.add(s); linked.add(tg); }
  const act = nodes.filter((k) => linked.has(k)), rest = nodes.filter((k) => !linked.has(k)), n = act.length;
  const ix = new Map(act.map((k, i) => [k, i])), x = new Float64Array(n), y = new Float64Array(n);
  let mx = 0, my = 0, sd = 0;
  act.forEach((k) => { const a = g.getNodeAttributes(k); mx += a.ox / n; my += a.oy / n; });
  act.forEach((k) => { const a = g.getNodeAttributes(k); sd += ((a.ox - mx) ** 2 + (a.oy - my) ** 2) / n; });
  sd = Math.sqrt(sd) || 1;
  act.forEach((k, i) => { const a = g.getNodeAttributes(k), ang = i * 2.399963; x[i] = (a.ox - mx) / sd + 0.02 * Math.cos(ang); y[i] = (a.oy - my) / sd + 0.02 * Math.sin(ang); });
  const k = 1.9 / Math.sqrt(n || 1), dx = new Float64Array(n), dy = new Float64Array(n), ITER = n > 500 ? 80 : 220;
  for (let it = 0; it < ITER; it++) {
    dx.fill(0); dy.fill(0);
    for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) {
      const ux = x[i] - x[j], uy = y[i] - y[j], d2 = ux * ux + uy * uy + 1e-6, f = k * k / d2;
      dx[i] += ux * f; dy[i] += uy * f; dx[j] -= ux * f; dy[j] -= uy * f;
    }
    for (const [s, tg, w] of E) {
      const i = ix.get(s), j = ix.get(tg), ux = x[i] - x[j], uy = y[i] - y[j], d = Math.sqrt(ux * ux + uy * uy) + 1e-6, f = d / k * (0.25 + 0.75 * w) * 0.35;
      dx[i] -= ux * f; dy[i] -= uy * f; dx[j] += ux * f; dy[j] += uy * f;
    }
    const temp = 0.15 * (1 - it / ITER) + 0.003;
    for (let i = 0; i < n; i++) {
      dx[i] -= x[i] * 0.45; dy[i] -= y[i] * 0.45;
      const len = Math.sqrt(dx[i] * dx[i] + dy[i] * dy[i]) + 1e-9, step = Math.min(len, temp);
      x[i] += dx[i] / len * step; y[i] += dy[i] / len * step;
    }
  }
  let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
  act.forEach((key, i) => { g.mergeNodeAttributes(key, { x: x[i], y: y[i] }); x0 = Math.min(x0, x[i]); x1 = Math.max(x1, x[i]); y0 = Math.min(y0, y[i]); y1 = Math.max(y1, y[i]); });
  if (!n) { x0 = -1; x1 = 1; y0 = 0; y1 = 0; }
  if (rest.length) {
    const w = Math.max(x1 - x0, 1.2), perRow = Math.max(8, Math.min(rest.length, Math.round(w / 0.085))), gap = w / perRow;
    rest.sort((a, b) => g.getNodeAttribute(a, "label").localeCompare(g.getNodeAttribute(b, "label")));
    rest.forEach((key, q) => { g.mergeNodeAttributes(key, { x: x0 + gap * (q % perRow + 0.5), y: y0 - 0.25 - gap * 1.1 * Math.floor(q / perRow) }); });
    y0 -= 0.25 + gap * 1.1 * Math.ceil(rest.length / perRow); x1 = Math.max(x1, x0 + w);
  }
  const pad = 0.07 * Math.max(x1 - x0, y1 - y0, 0.5);
  return { x: [x0 - pad, x1 + pad], y: [y0 - pad, y1 + pad] };
}

function writeHash() {
  if (state.restoring) return;
  const q = new URLSearchParams();
  if (state.structFocus) q.set("d", state.structFocus);
  if (state.structWith) q.set("w", state.structWith);
  if (state.focus !== null) q.set("c", state.focus);
  if (state.lens !== "all") q.set("l", state.lens);
  if (state.selected) q.set("p", state.selected);
  if (!state.selected && state.bridgeA) q.set("ba", state.bridgeA);
  if (!state.selected && state.bridgeB) q.set("bb", state.bridgeB);
  try { history.replaceState(null, "", q.toString() ? "#" + q.toString() : location.pathname + location.search); } catch { /* file:// or sandbox */ }
}

function readHash() {
  let q; try { q = new URLSearchParams(location.hash.slice(1)); } catch { return; }
  state.restoring = true;
  if (LENSES.includes(q.get("l"))) state.lens = q.get("l");
  if (q.get("c") !== null && state.data.communities.some((c) => String(c.id) === q.get("c"))) state.focus = +q.get("c");
  const d = q.get("d");
  buildLenses();
  setStruct(d && state.structIndex.has(d) ? d : "", q.get("w"));
  if (q.get("p") && state.graph.hasNode(q.get("p"))) {
    select(q.get("p"), false);
  } else if (q.get("ba") && state.graph.hasNode(q.get("ba"))) {
    const bd = document.getElementById("bridge-details");
    if (bd) bd.open = true;
    setBridgePair(q.get("ba"), q.get("bb") && state.graph.hasNode(q.get("bb")) ? q.get("bb") : null);
  }
  state.restoring = false;
  writeHash();
}

// ---- Matrix: structures against structures ----
function unitAcronym(name) {
  const s = shortUnit(name);
  const m = s.match(/-\s*([A-Z0-9]{3,8})$/);
  if (m) return m[1];
  const map = {
    "Ingegneria Civile Ambientale e Meccanica": "DICAM",
    "Ingegneria e Scienza dell'Informazione": "DISI",
    "Ingegneria Industriale": "DII",
    "Economia e Management": "DEM",
    "Sociologia e Ricerca Sociale": "DSRS",
    "Psicologia e Scienze Cognitive": "DIPSCO",
    "Lettere e Filosofia": "Lettere",
    "Giurisprudenza": "Giurispr.",
    "Matematica": "Matem.",
    "Fisica": "Fisica",
  };
  return map[s] || s.slice(0, 10);
}

function openMatrix() {
  const g = state.graph, names = state.structs.map(([a]) => a), ix = new Map(names.map((a, i) => [a, i])), N = names.length;
  const kinds = { m_unexplored: (a) => a.unexplored, m_links: () => true, m_bridge: (a) => a.raw.coauth > 0 };
  const kind = state.matrixKind || "m_unexplored", M = Array.from({ length: N }, () => new Array(N).fill(0));
  g.forEachEdge((e, a, s, tg, sa, ta) => {
    const i = ix.get(sa.dept), j = ix.get(ta.dept);
    if (i === undefined || j === undefined || !kinds[kind](a)) return;
    M[i][j] += 1; if (i !== j) M[j][i] += 1;
  });
  let max = 1; for (let i = 0; i < N; i++) for (let j = 0; j < N; j++) if (i !== j) max = Math.max(max, M[i][j]);
  const cell = (i, j) => {
    const v = M[i][j], k = i === j ? 0 : Math.sqrt(v / max);
    const style = i === j || !v ? "" : `background:rgba(${DARK ? "41,151,255" : "0,113,227"},${(0.10 + 0.82 * k).toFixed(3)});color:${k > 0.52 ? "#fff" : "inherit"}`;
    const cls = i === j ? "diag" : v ? "hit" : "zero";
    const tip = `${shortUnit(names[i])} ↔ ${shortUnit(names[j])}: ${v} (${t(kind)})`;
    return `<td class="${cls}" style="${style}" data-i="${i}" data-j="${j}" data-tip="${esc(tip)}">${i === j ? "—" : v || "·"}</td>`;
  };
  const box = document.getElementById("matrix");
  box.innerHTML = `<div class="sheet glass"><div class="mhead"><h2>${t("matrix_title")}</h2>` +
    `<div class="seg">${Object.keys(kinds).map((q) => `<button type="button" data-k="${q}" class="${q === kind ? "on" : ""}">${t(q)}</button>`).join("")}</div>` +
    `<button type="button" class="pill" id="matrix-close">${t("close")}</button></div><p>${t("matrix_help")}</p>` +
    `<div class="mscroll"><table><thead><tr><th></th>${names.map((a) => `<th class="col" data-tip="${esc(shortUnit(a))}"><span>${esc(unitAcronym(a))}</span></th>`).join("")}</tr></thead>` +
    `<tbody>${names.map((a, i) => `<tr><th data-tip="${esc(a)}">${esc(shortUnit(a))}</th>${names.map((_, j) => cell(i, j)).join("")}</tr>`).join("")}</tbody></table></div></div>`;
  box.hidden = false;
  box.querySelectorAll("[data-k]").forEach((b) => { b.onclick = () => { state.matrixKind = b.dataset.k; openMatrix(); }; });
  document.getElementById("matrix-close").onclick = closeMatrix;
  box.onclick = (ev) => { if (ev.target === box) closeMatrix(); };
  box.querySelectorAll("td.hit").forEach((td) => { td.onclick = () => {
    const i = +td.dataset.i, j = +td.dataset.j;
    closeMatrix();
    state.focus = null; state.lens = kind === "m_unexplored" ? "unexplored" : kind === "m_bridge" ? "bridge" : "all";
    select(null);
    setTab("explore");
    buildLenses();
    setStruct(names[i], state.lens === "all" ? "" : names[j]);
  }; });
}
function closeMatrix() { document.getElementById("matrix").hidden = true; }

function openAbout() {
  const box = document.getElementById("about");
  if (!box) return;
  box.innerHTML = `<div class="sheet glass">` +
    `<div class="mhead"><h2>${esc(t("about_title"))}</h2>` +
    `<button type="button" class="pill" id="about-close">${esc(t("close"))}</button></div>` +
    `<p>${esc(t("about_p1"))}</p>` +
    `<p class="about-muted">${esc(t("about_p2"))}</p>` +
    `<div class="about-card">` +
    `<span class="about-label">${esc(t("about_credits_label"))}</span>` +
    `<div class="about-names">Sebastiano Franchini · Roberto Zamparelli</div>` +
    `<div class="about-sub">${esc(t("about_credits_sub"))}</div>` +
    `</div></div>`;
  box.hidden = false;
  document.getElementById("about-close").onclick = closeAbout;
  box.onclick = (ev) => { if (ev.target === box) closeAbout(); };
}
function closeAbout() {
  const box = document.getElementById("about");
  if (box) box.hidden = true;
}

function downloadPairs() {
  const g = state.graph, q = (v) => `"${String(v == null ? "" : v).replace(/"/g, '""')}"`, rows = [["persona_a", "struttura_a", "persona_b", "struttura_b", "semantica_pct", "didattica_pct", "pubblicazioni_insieme", "motivo"]];
  for (const r of state.pairRows || []) {
    const A = g.getNodeAttributes(r.s), B = g.getNodeAttributes(r.tg), ev = r.a.ev || {};
    rows.push([A.label, A.dept, B.label, B.dept, r.a.p.sem === undefined ? "" : (100 * r.a.p.sem).toFixed(0), r.a.p.teach === undefined ? "" : (100 * r.a.p.teach).toFixed(0),
      (ev.coauth || []).length, pairWhy(r.a).replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"')]);
  }
  const url = URL.createObjectURL(new Blob(["\ufeff" + rows.map((r) => r.map(q).join(";")).join("\r\n")], { type: "text/csv;charset=utf-8" }));
  const a = document.createElement("a"); a.href = url; a.download = `coppie_${state.lens}.csv`; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

// Clean legend: displays either Communities or Structures based on legendMode + search filter.
function buildLegend() {
  const box = document.getElementById("legend-items");
  box.innerHTML = "";
  const q = (state.legendQuery || "").trim().toLowerCase();
  const add = (html, opts = {}) => {
    const s = document.createElement(opts.onclick ? "button" : "span");
    s.className = "swatch" + (opts.active ? " active" : "");
    s.innerHTML = html;
    if (opts.onclick) { s.title = opts.title || ""; s.onclick = opts.onclick; }
    box.appendChild(s);
  };
  const dot = (c, solid) => `<i class="${solid ? "" : "hollow"}" style="background:${c};--c:${c}"></i>`;
  const byComm = colorMode() === "community";
  const bar = (share, c) => `<div class="bar"><div style="width:${Math.max(3, 100 * share).toFixed(0)}%;background:${c}"></div></div>`;
  const real = state.data.communities.filter((c) => c.size >= MIN_COMMUNITY).sort((a, b) => b.size - a.size);

  document.querySelectorAll("#legend-mode button").forEach((b) => b.classList.toggle("on", b.dataset.mode === state.legendMode));

  if (state.legendMode === "communities") {
    for (const c of real) {
      const title = commTitle(c);
      const terms = (c.label || "").split(", ").slice(0, 5).join(", ");
      if (q && !title.toLowerCase().includes(q) && !terms.toLowerCase().includes(q)) continue;
      add(`${dot(communityColor(c.id), byComm)}<span><span class="t"><b>${esc(title)}</b><em>${c.size}</em></span>` +
          (terms ? `<small>${esc(terms)}</small>` : "") + bar(c.size / real[0].size, communityColor(c.id)) + `</span>`,
          { active: state.focus === c.id, title: t("focus_hint"),
            onclick: () => setFocus(state.focus === c.id ? null : c.id) });
    }
    const iso = state.data.nodes.filter(isIsolated).length;
    if (iso && !q) add(`${dot(ISOLATED_COLOR, true)}<span><b>${iso}</b> ${t("isolated")}</span>`);
  } else {
    for (const [name, count] of state.structs) {
      if (q && !name.toLowerCase().includes(q)) continue;
      add(`${dot(structColor(name), !byComm)}<span><span class="t"><b>${esc(shortUnit(name))}</b><em>${count}</em></span>${bar(count / state.structs[0][1], structColor(name))}</span>`,
        { active: state.structFocus === name, title: t("struct_hint"), onclick: () => setStruct(state.structFocus === name ? "" : name) });
    }
  }
  renderChips();
  const sd = document.getElementById("view-dept"), sc = document.getElementById("view-comm");
  sd.innerHTML = `<option value="">${t("view_all_dept")}</option>` + state.structs.map(([a, c]) => `<option value="${esc(a)}">${esc(shortUnit(a))} (${c})</option>`).join("");
  sd.value = state.structFocus;
  sc.innerHTML = `<option value="">${t("view_all_comm")}</option>` + real.map((c) => `<option value="${c.id}">${esc(commTitle(c))} (${c.size})</option>`).join("");
  sc.value = state.focus === null ? "" : String(state.focus);

  // Sync custom frosted-glass dropdowns for Department and Community
  const dLabel = document.getElementById("view-dept-label"), dMenu = document.getElementById("view-dept-menu");
  if (dLabel && dMenu) {
    dLabel.textContent = state.structFocus ? shortUnit(state.structFocus) : t("view_all_dept");
    dMenu.innerHTML = `<button type="button" class="dd-item ${!state.structFocus ? "active" : ""}" data-val=""><span class="dd-main"><span class="dd-text"><span>${esc(t("view_all_dept"))}</span></span></span></button>` +
      state.structs.map(([a, c]) => `<button type="button" class="dd-item ${state.structFocus === a ? "active" : ""}" data-val="${esc(a)}"><span class="dd-main"><i class="dd-dot" style="background:${structColor(a)}"></i><span class="dd-text"><span>${esc(shortUnit(a))}</span></span></span><em>${c}</em></button>`).join("");
    dMenu.querySelectorAll(".dd-item").forEach((b) => {
      b.onclick = () => { closeCustomSelects(); setStruct(b.dataset.val); };
    });
  }
  const cLabel = document.getElementById("view-comm-label"), cMenu = document.getElementById("view-comm-menu");
  if (cLabel && cMenu) {
    const activeComm = state.focus === null ? null : real.find((c) => c.id === state.focus);
    cLabel.textContent = activeComm ? commTitle(activeComm) : t("view_all_comm");
    cMenu.innerHTML = `<button type="button" class="dd-item ${state.focus === null ? "active" : ""}" data-val=""><span class="dd-main"><span class="dd-text"><span>${esc(t("view_all_comm"))}</span></span></span></button>` +
      real.map((c) => {
        const kw = (c.label || "").split(", ").slice(0, 4).join(", ");
        return `<button type="button" class="dd-item ${state.focus === c.id ? "active" : ""}" data-val="${c.id}"><span class="dd-main"><i class="dd-dot" style="background:${communityColor(c.id)}"></i><span class="dd-text"><span>${esc(commTitle(c))}</span>${kw ? `<small>${esc(kw)}</small>` : ""}</span></span><em>${c.size}</em></button>`;
      }).join("");
    cMenu.querySelectorAll(".dd-item").forEach((b) => {
      b.onclick = () => { closeCustomSelects(); setFocus(b.dataset.val); };
    });
  }
}

function renderChips() {
  const box = document.getElementById("chips");
  if (!box) return;
  box.innerHTML = "";
  const chip = (text, clear) => {
    const b = document.createElement("button");
    b.className = "chip glass";
    b.innerHTML = `<span>${text}</span><i aria-hidden="true">×</i>`;
    b.title = t("clear_filter");
    b.onclick = clear;
    box.appendChild(b);
  };
  if (state.focus !== null) {
    const c = state.data.communities.find((x) => x.id === state.focus);
    chip(`${t("communities")}: ${esc(c ? commTitle(c) : state.focus)}`, () => setFocus(null));
  }
  if (state.structFocus) chip(esc(shortUnit(state.structFocus)) + (state.structWith ? " ↔ " + esc(shortUnit(state.structWith)) : ""), () => setStruct(""));
  if (state.lens !== "all") chip(t("lens")[state.lens][0], () => setLens("all"));
  if (state.bridgeA && state.bridgeB && state.graph) {
    const la = state.graph.getNodeAttribute(state.bridgeA, "label"), lb = state.graph.getNodeAttribute(state.bridgeB, "label");
    chip(`${esc(la)} ↔ ${esc(lb)}`, () => setBridgePair(null, null, null));
  }
}

const colorMode = () => state.colorBy;
function nodeColor(n) {
  if (colorMode() === "community") return communityColor(n.community);
  return structColor(n.dept);
}

function link(doi, text) {
  return doi ? `<a href="https://doi.org/${encodeURI(doi)}" target="_blank" rel="noopener">${esc(text)}</a>` : esc(text);
}

// ---- Explore ----
function setLens(l) {
  state.lens = l;
  buildLenses(); buildExplore(); renderChips();
  applyFocus();
}

function buildLenses() {
  const box = document.getElementById("lenses");
  box.innerHTML = "";
  for (const l of LENSES) {
    const [name, help] = t("lens")[l];
    const b = document.createElement("button");
    b.type = "button";
    b.className = "lens" + (state.lens === l ? " on" : "");
    b.dataset.tip = help;
    b.innerHTML = `<span class="lens-left"><i class="lens-dot"></i><b>${name}</b></span>${l === "all" ? "" : `<em>${state.lensCount[l]}</em>`}`;
    b.onclick = () => setLens(l);
    box.appendChild(b);
  }
  const desc = document.getElementById("lens-desc");
  if (desc) desc.textContent = (t("lens")[state.lens] || [])[1] || "";
}

function passesFilters(s, tg) {
  const g = state.graph, need = state.lens === "all" ? 2 : 1;
  const sa = g.getNodeAttributes(s), ta = g.getNodeAttributes(tg);
  if (state.structFocus && state.structWith) {
    if (!((inStruct(sa) && ta.dept === state.structWith) || (inStruct(ta) && sa.dept === state.structWith))) return false;
  } else if (state.structFocus && inStruct(sa) + inStruct(ta) < need) return false;
  if (state.focus !== null && (g.getNodeAttribute(s, "community") === state.focus) + (g.getNodeAttribute(tg, "community") === state.focus) < need) return false;
  return true;
}

function pairWhy(a) {
  const ev = a.ev || {};
  if (state.lens === "unexplored" && ev.sem && ev.sem[0]) return `«${esc(ev.sem[0].a)}» ↔ «${esc(ev.sem[0].b)}»`;
  if (state.lens === "coteach" && ev.teach) return `${t("shared_courses")}: ${esc((ev.teach.shared || []).slice(0, 3).join("; "))}`;
  if (state.lens === "teach" && ev.teach && ev.teach.courses && ev.teach.courses[0]) return `${t("similar_courses")}: ${esc(ev.teach.courses[0].a)} ↔ ${esc(ev.teach.courses[0].b)}`;
  if (state.lens === "bridge" && ev.coauth && ev.coauth[0]) return `${t("joint_pubs")}: «${esc(ev.coauth[0].title)}»${ev.coauth.length > 1 ? " …" : ""}`;
  return "";
}

function pairScore(a) {
  if (state.lens === "unexplored" && a.p.sem !== undefined) return `<span class="score" data-tip="${esc(t("tip_pct"))}">${(a.p.sem * 100).toFixed(0)}° pct</span>`;
  if (state.lens === "coteach" && a.ev && a.ev.teach && a.ev.teach.shared) return `<span class="score">${a.ev.teach.shared.length}</span>`;
  if (state.lens === "teach" && a.p.teach !== undefined) return `<span class="score" data-tip="${esc(t("tip_pct"))}">${(a.p.teach * 100).toFixed(0)}° pct</span>`;
  if (state.lens === "bridge" && a.ev && a.ev.coauth) return `<span class="score">${a.ev.coauth.length} ${t("pubs")}</span>`;
  return "";
}

function buildExplore() {
  const g = state.graph;
  const card = document.getElementById("dept-card"), box = document.getElementById("pairs");
  card.hidden = !state.structFocus && state.focus === null;
  if (!state.structFocus && state.focus !== null) {
    const c = state.data.communities.find((q) => q.id === state.focus) || {}, members = state.data.nodes.filter((n) => n.community === state.focus), by = new Map();
    for (const n of members) if (n.dept) by.set(n.dept, (by.get(n.dept) || 0) + 1);
    card.innerHTML = `<div class="dept-card-head"><div><h3>${esc(commTitle(c))}</h3><p>${members.length} ${t("dept_people")}${c.label ? " · " + esc(c.label) : ""}</p></div>` +
      `<button type="button" class="pill subtle" id="dept-print">${t("print")}</button></div><h4>${t("comm_depts")}</h4>` +
      [...by].sort((a, b) => b[1] - a[1]).slice(0, 6).map(([d, k]) => `<button type="button" class="deptlink comm" data-d="${esc(d)}"><span><i style="background:${structColor(d)}"></i>${esc(shortUnit(d))}</span><em>${k} · ${(100 * k / members.length).toFixed(0)}%</em></button>`).join("");
    card.querySelectorAll(".deptlink").forEach((b) => { b.onclick = () => { if (state.structIndex.has(b.dataset.d) && isUnit(b.dataset.d)) { state.focus = null; setStruct(b.dataset.d); } }; });
    const pr = document.getElementById("dept-print"); if (pr) pr.onclick = () => window.print();
  }
  if (state.structFocus) {
    const members = state.data.nodes.filter(inStruct);
    const other = new Map();
    g.forEachEdge((e, a, s, tg, sa, ta) => {
      const is = inStruct(sa), it = inStruct(ta);
      if (is === it) return;
      const d = (is ? ta : sa).dept;
      if (!d || !isUnit(d)) return;
      const o = other.get(d) || { links: 0, unexplored: 0 };
      o.links += 1; o.unexplored += a.unexplored ? 1 : 0;
      other.set(d, o);
    });
    const top = [...other].sort((x, y) => y[1].links - x[1].links).slice(0, 6);
    card.innerHTML = `<div class="dept-card-head"><div><h3>${esc(state.structFocus)}</h3><p>${members.length} ${t("dept_people")} · ${members.filter((n) => n.layers.sem).length} ${t("dept_sem")}</p></div>` +
      `<button type="button" class="pill subtle" id="dept-print">${t("print")}</button></div>` +
      (() => { const by = new Map(); for (const n of members) if (communityRank().has(n.community)) by.set(n.community, (by.get(n.community) || 0) + 1);
        const cs = [...by].sort((a, b) => b[1] - a[1]).slice(0, 5);
        return cs.length ? `<h4>${t("dept_comms")}</h4>` + cs.map(([id, k]) => { const c = state.data.communities.find((q) => q.id === id) || {};
          return `<button type="button" class="deptlink comm" data-c="${id}"><span><i style="background:${communityColor(id)}"></i>${esc((c.label || c.name || "").split(", ").slice(0, 3).join(", "))}</span><em>${k}</em></button>`; }).join("") : ""; })() +
      (top.length ? `<h4>${t("dept_links")}</h4>` + top.map(([d, o]) => `<button type="button" class="deptlink" data-d="${esc(d)}"><span>${esc(shortUnit(d))}</span><em>${o.links} ${t("dept_l")} · ${o.unexplored} ${t("dept_u")}</em></button>`).join("") : "");
    card.querySelectorAll(".deptlink[data-d]").forEach((b) => { b.onclick = () => setStruct(b.dataset.d); });
    card.querySelectorAll(".deptlink[data-c]").forEach((b) => { b.onclick = () => setFocus(state.focus === +b.dataset.c ? null : b.dataset.c); });
    const pr = document.getElementById("dept-print"); if (pr) pr.onclick = () => window.print();
  }
  box.hidden = state.lens === "all";
  if (state.lens === "all") return;
  const key = { unexplored: (a) => (a.p.sem || 0) + 0.001 * ((a.conf || {}).sem || 0), coteach: (a) => ((a.ev.teach || {}).shared || []).length + (a.p.teach || 0),
                teach: (a) => a.p.teach || 0, bridge: (a) => a.raw.coauth || 0 }[state.lens];
  const rows = [];
  g.forEachEdge((e, a, s, tg) => { if (lensMatch(a) && passesFilters(s, tg)) rows.push({ a, s, tg, k: key(a) }); });
  rows.sort((x, y) => y.k - x.k);
  state.pairRows = rows;
  const SHOW = 60;
  box.innerHTML = `<p class="count"><span>${rows.length} ${t("pairs_count")}${rows.length > SHOW ? ` · ${t("pairs_shown")} ${SHOW}` : ""}</span>${rows.length ? `<button type="button" class="pill subtle" id="csv">${t("csv")}</button>` : ""}</p>` +
    (rows.length ? "" : `<p class="ev">${t("pairs_none")}</p>`) +
    rows.slice(0, SHOW).map((r) => {
      const A = g.getNodeAttributes(r.s), B = g.getNodeAttributes(r.tg), why = pairWhy(r.a);
      return `<div class="pair" data-s="${esc(r.s)}" data-t="${esc(r.tg)}"><div class="neigh-top"><span><b data-id="${esc(r.s)}">${esc(A.label)}</b> ↔ <b data-id="${esc(r.tg)}">${esc(B.label)}</b></span>${pairScore(r.a)}</div>` +
        `<small>${esc(shortUnit(A.dept) || t("no_data"))} · ${esc(shortUnit(B.dept) || t("no_data"))}</small>${why ? `<div class="why">${why}</div>` : ""}</div>`;
    }).join("");
  box.querySelectorAll(".pair").forEach((el) => {
    el.onmouseenter = () => setHoverPair(el.dataset.s, el.dataset.t);
    el.onmouseleave = () => setHoverPair(null);
  });
  box.querySelectorAll("b[data-id]").forEach((b) => { b.onclick = () => select(b.dataset.id, true); });
  const csv = document.getElementById("csv"); if (csv) csv.onclick = downloadPairs;
}

function setHoverPair(s, tg) {
  if (!s) {
    state.hoverPair = null;
    state.hoverEdge = null;
  } else {
    state.hoverPair = tg ? [s, tg] : [s];
    state.hoverEdge = (tg && state.graph && state.graph.hasEdge(s, tg)) ? state.graph.edge(s, tg) : null;
  }
  if (state.renderer) state.renderer.refresh();
}

function evidenceHtml(layer, ev, isSource) {
  if (!ev) return "";
  const items = [];
  const cosTip = esc(t("tip_cos"));
  if (layer === "sem") for (const e of ev) items.push(`${link(isSource ? e.doi_a : e.doi_b, isSource ? e.a : e.b)} ↔ ${link(isSource ? e.doi_b : e.doi_a, isSource ? e.b : e.a)} (<span class="cos-badge" data-tip="${cosTip}">cos ${e.cos}</span>)`);
  if (layer === "coupling") for (const e of ev) items.push(`<a href="https://openalex.org/${encodeURI(e.ref)}" target="_blank" rel="noopener">${esc(e.ref)}</a> (${t("weight")} ${e.w})`);
  if (layer === "direct") for (const e of ev) items.push(`${esc(e.citing)} → ${t("cites")} → ${esc(e.cited)}`);
  if (layer === "coauth") for (const e of ev) items.push(`${link(e.doi, e.title)}${e.year ? " (" + e.year + ")" : ""}`);
  if (layer === "teach") {
    if ((ev.shared || []).length) items.push(`<b>${t("shared_courses")}</b>: ${esc(ev.shared.join("; "))}`);
    items.push(`${t("shared_programmes")}: ${esc((ev.programmes || []).join(", ")) || t("none")}`);
    for (const e of ev.courses || []) items.push(`${esc(isSource ? e.a : e.b)} ↔ ${esc(isSource ? e.b : e.a)} (<span class="cos-badge" data-tip="${cosTip}">cos ${e.cos}</span>)`);
  }
  if (layer === "field") items.push(`<span data-tip="${esc(t("tip_ssd"))}">${t("ssd")}: ${esc(ev.ssd_i || t("no_data"))} / ${esc(ev.ssd_j || t("no_data"))}</span>`);
  return items.length ? `<ul class="ev">${items.map((x) => `<li>${x}</li>`).join("")}</ul>` : "";
}

function showPanel(id) {
  const g = state.graph, n = g.getNodeAttributes(id);
  document.getElementById("panel-name").textContent = n.label;
  const badges = document.getElementById("panel-badges");
  badges.innerHTML = (n.dept ? `<button type="button" class="badge" id="panel-dept-btn" data-tip="${esc(t("tip_dept_select"))}">${esc(shortUnit(n.dept))}</button>` : "") +
    (n.role ? `<span class="badge">${esc(n.role)}</span>` : "") +
    (n.ssd ? `<span class="badge" data-tip="${esc(t("tip_ssd"))}">${t("ssd")} ${esc(n.ssd)}</span>` : "") +
    `<span class="badge">${n.n_pubs} ${t("pubs")}</span>`;
  const dbtn = document.getElementById("panel-dept-btn");
  if (dbtn) dbtn.onclick = () => { select(null); setStruct(n.dept); };

  const others = (n.affiliations || []).filter((a) => a !== n.dept);
  const metaEl = document.getElementById("panel-meta");
  metaEl.textContent = others.length ? `${t("affiliations")}: ${others.join("; ")}` : "";
  metaEl.hidden = !others.length;

  // Report issue mailto link (8.2)
  const email = (state.data.meta && state.data.meta.contact_email) || "";
  const subj = encodeURIComponent(t("report_subject") + ` — ${n.label}`);
  const body = encodeURIComponent(t("report_body").replace("{name}", n.label).replace("{id}", id).replace("{dept}", n.dept || "-").replace("{role}", n.role || "-").replace("{ssd}", n.ssd || "-"));
  document.getElementById("panel-report").href = `mailto:${email}?subject=${subj}&body=${body}`;

  // Courses
  document.getElementById("panel-courses-count").textContent = `(${n.courses.length})`;
  const cl = document.getElementById("panel-courses");
  cl.innerHTML = n.courses.length ? n.courses.map((c) => `<li>${esc(c.name)}${c.programme ? " — " + esc(c.programme) : ""} (${esc(c.year)})</li>`).join("") : `<li>${t("none")}</li>`;

  // Quick neighbour scope filter (All | Other depts | Unexplored)
  const scopeBox = document.getElementById("panel-scope-tabs");
  if (scopeBox) {
    scopeBox.innerHTML =
      `<button type="button" class="${state.panelScope === "all" ? "on" : ""}" data-sc="all">${t("scope_all")}</button>` +
      `<button type="button" class="${state.panelScope === "cross" ? "on" : ""}" data-sc="cross" data-tip="${esc(t("tip_scope_cross"))}">${t("scope_cross")}</button>` +
      `<button type="button" class="${state.panelScope === "unexplored" ? "on" : ""}" data-sc="unexplored" data-tip="${esc(t("tip_scope_unexplored"))}">${t("scope_unexplored")}</button>`;
    scopeBox.querySelectorAll("button").forEach((b) => {
      b.onclick = () => {
        state.panelScope = b.dataset.sc;
        showPanel(id);
        applyFocus(false);
      };
    });
  }

  // Layer segmented switcher
  const shown = layersShown();
  if (state.panelLayer !== "all" && !shown.includes(state.panelLayer)) state.panelLayer = "all";
  const pillBox = document.getElementById("panel-layer-tabs");
  const shortLabels = t("layers_short") || t("layers");
  pillBox.innerHTML = `<button type="button" class="${state.panelLayer === "all" ? "on" : ""}" data-l="all">${t("all_layers")}</button>` +
    shown.map((l) => `<button type="button" class="${state.panelLayer === l ? "on" : ""}" data-l="${l}" data-tip="${esc(t("layer_help")[l])}">${shortLabels[l] || t("layers")[l]}</button>`).join("");
  pillBox.querySelectorAll("button").forEach((b) => { b.onclick = () => { state.panelLayer = b.dataset.l; showPanel(id); }; });

  const box = document.getElementById("panel-neighbours");
  box.innerHTML = "";
  const activeLayers = state.panelLayer === "all" ? shown : [state.panelLayer];
  const limit = state.panelLayer === "all" ? 3 : 8;
  for (const l of activeLayers) {
    const rows = [];
    g.forEachEdge(id, (e, a, s, tgt) => {
      if (a.p[l] === undefined || !neighborMatchesScope(a)) return;
      const other = s === id ? tgt : s;
      rows.push({ other, p: a.p[l], raw: a.raw[l], ev: a.ev[l], conf: a.conf ? a.conf[l] : undefined, isSource: s === id, unexplored: a.unexplored });
    });
    rows.sort((x, y) => y.p - x.p);
    const h = document.createElement("h3");
    h.textContent = t("layers")[l];
    h.dataset.tip = t("layer_help")[l];
    box.appendChild(h);
    if (!rows.length || !n.layers[l]) { box.insertAdjacentHTML("beforeend", `<p class="ev">${t("no_data")}</p>`); continue; }
    for (const r of rows.slice(0, limit)) {
      const otherAttrs = g.getNodeAttributes(r.other);
      const pct = Math.max(4, Math.round(r.p * 100));
      const d = document.createElement("div");
      d.className = "neigh";
      d.innerHTML = `<div class="neigh-top"><b data-id="${esc(r.other)}">${esc(otherAttrs.label)}</b>` +
        `<span class="score" data-tip="${esc(t("tip_pct"))}">${(r.p * 100).toFixed(0)}° pct${l === "sem" ? "" : " · " + r.raw.toFixed(2)}</span></div>` +
        `<div class="neigh-sub"><span>${esc(shortUnit(otherAttrs.dept) || t("no_data"))}</span>` +
        (r.unexplored ? `<span class="tag" data-tip="${esc(t("tip_unexplored"))}">${t("unexplored_tag")}</span>` : "") +
        `${confidenceHtml(r.conf)}</div>` +
        `<div class="bar"><div style="width:${pct}%;background:var(--accent)"></div></div>` +
        evidenceHtml(l, r.ev, r.isSource);
      d.onmouseenter = () => setHoverPair(id, r.other);
      d.onmouseleave = () => setHoverPair(null);
      d.querySelector("b").onclick = () => select(r.other, true);
      box.appendChild(d);
    }
  }
}

function findBridgePath(src, dst) {
  const g = state.graph;
  if (!g || !src || !dst || src === dst || !g.hasNode(src) || !g.hasNode(dst)) return null;
  if (g.hasEdge(src, dst)) {
    return { nodes: [src, dst], edges: [g.edge(src, dst)], direct: true };
  }
  const dist = new Map([[src, 0]]), prev = new Map(), hops = new Map([[src, 0]]), visited = new Set();
  const pq = [[0, src]];
  while (pq.length) {
    pq.sort((a, b) => a[0] - b[0]);
    const [d, u] = pq.shift();
    if (visited.has(u)) continue;
    visited.add(u);
    if (u === dst) break;
    const h = hops.get(u) || 0;
    if (h >= 4) continue;
    g.forEachEdge(u, (e, a, s, tg) => {
      if (a.w === null || a.w <= 0.1) return;
      const v = s === u ? tg : s;
      if (visited.has(v)) return;
      const cost = 0.4 + (1.02 - Math.min(1, Math.max(0.05, a.w)));
      const nd = d + cost;
      if (nd < (dist.get(v) ?? Infinity)) {
        dist.set(v, nd);
        hops.set(v, h + 1);
        prev.set(v, [u, e]);
        pq.push([nd, v]);
      }
    });
  }
  if (!prev.has(dst)) return null;
  const nodes = [dst], edges = [];
  let cur = dst;
  while (cur !== src) {
    const [p, e] = prev.get(cur);
    nodes.push(p);
    edges.push(e);
    cur = p;
  }
  nodes.reverse();
  edges.reverse();
  return { nodes, edges, direct: false };
}

function topLayersText(a) {
  const shortLabels = t("layers_short") || t("layers");
  return layersShown()
    .filter((l) => a.p && a.p[l] !== undefined)
    .sort((x, y) => a.p[y] - a.p[x])
    .slice(0, 3)
    .map((l) => `${esc(shortLabels[l])}: ${(a.p[l] * 100).toFixed(0)}° pct`)
    .join(" · ");
}

function syncBridgePicking() {
  const inpA = document.getElementById("bridge-input-a"), inpB = document.getElementById("bridge-input-b");
  if (inpA) inpA.classList.toggle("picking", state.bridgePickSlot === "a");
  if (inpB) inpB.classList.toggle("picking", state.bridgePickSlot === "b");
}

function renderBridge() {
  const out = document.getElementById("bridge-out"), clr = document.getElementById("bridge-clear");
  const inpA = document.getElementById("bridge-input-a"), inpB = document.getElementById("bridge-input-b");
  if (!out || !clr) return;
  const g = state.graph;
  if (inpA && g) inpA.value = state.bridgeA && g.hasNode(state.bridgeA) ? g.getNodeAttribute(state.bridgeA, "label") : "";
  if (inpB && g) inpB.value = state.bridgeB && g.hasNode(state.bridgeB) ? g.getNodeAttribute(state.bridgeB, "label") : "";
  clr.hidden = !state.bridgeA && !state.bridgeB;
  syncBridgePicking();
  const introEl = document.getElementById("intro");
  if (introEl) introEl.hidden = !!state.view || !!state.selected || !!(state.bridgeA && state.bridgeB);
  if (!state.bridgeA || !state.bridgeB || !g) {
    out.hidden = true;
    return;
  }
  out.hidden = false;
  const res = findBridgePath(state.bridgeA, state.bridgeB);
  if (!res) {
    out.innerHTML = `<p class="ev">${esc(t("bridge_none"))}</p>`;
    return;
  }
  const chainHtml = [];
  chainHtml.push(`<div class="neigh-sub" style="margin-bottom:2px"><span class="tag">${esc(res.direct ? t("bridge_direct") : `${t("bridge_path")} (${res.edges.length} hop)`)}</span></div>`);
  for (let i = 0; i < res.nodes.length; i++) {
    const nid = res.nodes[i], na = g.getNodeAttributes(nid);
    chainHtml.push(`<div class="bridge-step" data-node="${esc(nid)}"><b data-id="${esc(nid)}">${esc(na.label)}</b><small>${esc(shortUnit(na.dept) || t("no_data"))}${na.ssd ? " · " + esc(na.ssd) : ""}</small></div>`);
    if (i < res.edges.length) {
      const e = res.edges[i], ea = g.getEdgeAttributes(e), s = res.nodes[i], tg = res.nodes[i + 1];
      const topLayers = topLayersText(ea);
      const evSem = ea.ev && ea.ev.sem && ea.ev.sem[0] ? `«${esc(ea.ev.sem[0].a)}» ↔ «${esc(ea.ev.sem[0].b)}»` : "";
      const evCo = ea.ev && ea.ev.coauth && ea.ev.coauth[0] ? `${t("joint_pubs")}: «${esc(ea.ev.coauth[0].title)}»` : "";
      const snippet = evCo || evSem;
      chainHtml.push(`<div class="bridge-hop" data-s="${esc(s)}" data-t="${esc(tg)}"><div><b>${((ea.w || 0) * 100).toFixed(0)}%</b> · ${topLayers}</div>${snippet ? `<div style="margin-top:2px;color:var(--fg)">${snippet}</div>` : ""}</div>`);
    }
  }
  out.innerHTML = `<div class="bridge-chain">${chainHtml.join("")}</div>`;
  out.querySelectorAll(".bridge-step").forEach((el) => {
    el.onmouseenter = () => setHoverPair(el.dataset.node, null);
    el.onmouseleave = () => setHoverPair(null);
  });
  out.querySelectorAll(".bridge-hop").forEach((el) => {
    el.onmouseenter = () => setHoverPair(el.dataset.s, el.dataset.t);
    el.onmouseleave = () => setHoverPair(null);
  });
  out.querySelectorAll(".bridge-step b[data-id]").forEach((b) => {
    b.onclick = () => select(b.dataset.id);
  });
}

function setBridgePair(a, b, nextSlot = undefined) {
  const g = state.graph;
  state.bridgeA = a && g && g.hasNode(a) ? a : null;
  state.bridgeB = b && g && g.hasNode(b) && b !== state.bridgeA ? b : null;
  if (state.bridgeA && state.bridgeB) {
    const res = findBridgePath(state.bridgeA, state.bridgeB);
    state.bridgePath = res ? res.nodes : [state.bridgeA, state.bridgeB];
    state.bridgeEdges = new Set(res ? res.edges : []);
    state.bridgePickSlot = null;
  } else {
    state.bridgePath = state.bridgeA ? [state.bridgeA] : (state.bridgeB ? [state.bridgeB] : null);
    state.bridgeEdges = null;
    if (nextSlot !== undefined) {
      state.bridgePickSlot = nextSlot;
    } else {
      const bd = document.getElementById("bridge-details");
      state.bridgePickSlot = (bd && bd.open) ? (!state.bridgeA ? "a" : "b") : null;
    }
  }
  renderBridge();
  renderChips();
  writeHash();
  if (state.renderer) state.renderer.refresh();
}

function setupBridgeFinder() {
  const bd = document.getElementById("bridge-details");
  const clr = document.getElementById("bridge-clear");
  if (!bd || !clr) return;
  clr.onclick = (ev) => {
    ev.preventDefault();
    ev.stopPropagation();
    setBridgePair(null, null, "a");
  };
  bd.addEventListener("toggle", () => {
    if (bd.open) {
      if (!state.bridgeA) state.bridgePickSlot = "a";
      else if (!state.bridgeB) state.bridgePickSlot = "b";
      else state.bridgePickSlot = null;
      syncBridgePicking();
    } else {
      state.bridgePickSlot = null;
      if (state.bridgeA || state.bridgeB) setBridgePair(null, null, null);
      else syncBridgePicking();
    }
  });
  const bindInput = (inputId, resId, isA) => {
    const input = document.getElementById(inputId), box = document.getElementById(resId);
    if (!input || !box) return;
    let activeIdx = -1, matches = [];
    const close = () => { box.hidden = true; activeIdx = -1; matches = []; };
    input.onfocus = () => {
      state.bridgePickSlot = isA ? "a" : "b";
      syncBridgePicking();
      input.select();
    };
    input.oninput = () => {
      const q = input.value.trim().toLowerCase();
      if (!q) {
        close();
        if (isA && state.bridgeA) setBridgePair(null, state.bridgeB, "a");
        else if (!isA && state.bridgeB) setBridgePair(state.bridgeA, null, "b");
        return;
      }
      if (!state.data) { close(); return; }
      const other = isA ? state.bridgeB : state.bridgeA;
      matches = state.data.nodes.filter((n) =>
        n.id !== other && (
          n.label.toLowerCase().includes(q) ||
          (n.dept || "").toLowerCase().includes(q) ||
          (n.ssd || "").toLowerCase().includes(q)
        )
      ).slice(0, 6);
      if (!matches.length) { close(); return; }
      activeIdx = 0;
      box.innerHTML = matches.map((n, i) =>
        `<button type="button" class="s-item ${i === 0 ? "active" : ""}" data-id="${esc(n.id)}">` +
        `<b>${esc(n.label)}</b><small>${esc(shortUnit(n.dept) || t("no_data"))}${n.ssd ? " · " + esc(n.ssd) : ""}</small></button>`
      ).join("");
      box.hidden = false;
      box.querySelectorAll(".s-item").forEach((b) => {
        b.onmousedown = (ev) => {
          ev.preventDefault();
          close();
          input.blur();
          if (isA) setBridgePair(b.dataset.id, state.bridgeB);
          else setBridgePair(state.bridgeA, b.dataset.id);
        };
      });
    };
    input.onkeydown = (ev) => {
      if (box.hidden || !matches.length) return;
      if (ev.key === "ArrowDown") { ev.preventDefault(); activeIdx = (activeIdx + 1) % matches.length; }
      else if (ev.key === "ArrowUp") { ev.preventDefault(); activeIdx = (activeIdx - 1 + matches.length) % matches.length; }
      else if (ev.key === "Enter" && activeIdx >= 0) {
        ev.preventDefault();
        const id = matches[activeIdx].id;
        close();
        input.blur();
        if (isA) setBridgePair(id, state.bridgeB);
        else setBridgePair(state.bridgeA, id);
        return;
      } else if (ev.key === "Escape") { close(); return; }
      box.querySelectorAll(".s-item").forEach((el, i) => el.classList.toggle("active", i === activeIdx));
    };
    input.onblur = () => setTimeout(() => {
      close();
      const g = state.graph;
      const cur = isA ? state.bridgeA : state.bridgeB;
      input.value = (cur && g && g.hasNode(cur)) ? g.getNodeAttribute(cur, "label") : "";
    }, 150);
  };
  bindInput("bridge-input-a", "bridge-results-a", true);
  bindInput("bridge-input-b", "bridge-results-b", false);
}

function confidenceHtml(c) {
  if (c === undefined) return "";
  const level = c >= 0.75 ? "high" : c >= 0.5 ? "mid" : "low";
  return `<span class="conf ${level}" data-tip="${esc(t("confidence_help"))}">${t("confidence")}: ${(c * 100).toFixed(0)}%</span>`;
}

function select(id) {
  state.selected = id || null;
  state.hoverNode = null; state.hoverT = 0; state.hoverTarget = 0;
  state.hoverPair = null; state.hoverEdge = null; state.hoveredEdge = null;
  if (id) state.bridgePickSlot = null;
  syncBridgePicking();
  setTab(state.tab);
  if (id) {
    showPanel(id);
    document.getElementById("panel").scrollTo({ top: 0, behavior: "smooth" });
  }
  applyFocus();
}

function edgeVisible(e, a) {
  if (state.hoverEdge === e || state.hoveredEdge === e) return true;
  if (!state.selected && state.bridgeEdges && state.bridgeEdges.has(e)) return true;
  const s = state.graph.source(e), tg = state.graph.target(e), v = state.view;
  if (state.selected) return (s === state.selected || tg === state.selected) && neighborMatchesScope(a);
  if (a.w === null || !passesFilters(s, tg)) return false;
  if (state.lens !== "all") return lensMatch(a);
  return !!(v && v.single) || a.w >= state.threshold;
}

function hoverTo(node) {
  if (node) { state.hoverNode = node; state.hoverTarget = 1; } else { state.hoverTarget = 0; }
  if (REDUCED) { state.hoverT = state.hoverTarget; if (!node) state.hoverNode = null; state.renderer.refresh(); return; }
  if (state.hoverRaf) return;
  let last = performance.now();
  const tick = (now) => {
    const dt = Math.min(64, now - last); last = now;
    state.hoverT += (state.hoverTarget - state.hoverT) * (1 - Math.exp(-dt / 90));
    if (Math.abs(state.hoverTarget - state.hoverT) < 0.01) {
      state.hoverT = state.hoverTarget;
      if (state.hoverTarget === 0) state.hoverNode = null;
      state.hoverRaf = 0;
    } else {
      state.hoverRaf = requestAnimationFrame(tick);
    }
    state.renderer.refresh();
  };
  state.hoverRaf = requestAnimationFrame(tick);
}

// Custom search autocomplete dropdown showing Name + Department + Role/SSD
function setupSearch() {
  const input = document.getElementById("search");
  const box = document.getElementById("search-results");
  let activeIdx = -1, matches = [];

  const closeSearch = () => { box.hidden = true; activeIdx = -1; matches = []; };
  const renderSearch = () => {
    const q = input.value.trim().toLowerCase();
    if (!q || !state.data) { closeSearch(); return; }
    matches = state.data.nodes.filter((n) =>
      n.label.toLowerCase().includes(q) ||
      (n.dept || "").toLowerCase().includes(q) ||
      (n.ssd || "").toLowerCase().includes(q)
    ).slice(0, 8);
    if (!matches.length) { closeSearch(); return; }
    activeIdx = 0;
    box.innerHTML = matches.map((n, i) =>
      `<button type="button" class="s-item ${i === 0 ? "active" : ""}" data-id="${esc(n.id)}">` +
      `<b>${esc(n.label)}</b><small>${esc(shortUnit(n.dept) || t("no_data"))}${n.role ? " · " + esc(n.role) : ""}${n.ssd ? " · " + esc(n.ssd) : ""}</small></button>`
    ).join("");
    box.hidden = false;
    box.querySelectorAll(".s-item").forEach((b) => {
      b.onmousedown = (ev) => { ev.preventDefault(); select(b.dataset.id, true); input.value = ""; closeSearch(); input.blur(); };
    });
  };

  input.oninput = () => {
    const exact = state.graph && state.graph.findNode((n, a) => a.label === input.value);
    if (exact) { select(exact, true); closeSearch(); return; }
    renderSearch();
  };
  input.onkeydown = (ev) => {
    if (box.hidden || !matches.length) return;
    if (ev.key === "ArrowDown") { ev.preventDefault(); activeIdx = (activeIdx + 1) % matches.length; }
    else if (ev.key === "ArrowUp") { ev.preventDefault(); activeIdx = (activeIdx - 1 + matches.length) % matches.length; }
    else if (ev.key === "Enter" && activeIdx >= 0) {
      ev.preventDefault();
      select(matches[activeIdx].id, true);
      input.value = ""; closeSearch(); input.blur();
      return;
    } else if (ev.key === "Escape") { closeSearch(); return; }
    box.querySelectorAll(".s-item").forEach((el, i) => el.classList.toggle("active", i === activeIdx));
  };
  input.onblur = () => setTimeout(closeSearch, 150);
}

function init(data, isSwitch = false) {
  state.data = data;
  state._rank = null;
  for (const l of data.meta.layers) {
    state.defaultWeights[l] = Number(data.meta.weights[l]);
    state.weights[l] = state.defaultWeights[l];
    state.enabled[l] = true;
  }
  const g = new UndirectedGraph();
  const maxPubs = Math.max(1, ...data.nodes.map((n) => n.n_pubs));
  const iso = data.nodes.filter(isIsolated).sort((a, b) => (a.dept || "").localeCompare(b.dept || "") || a.label.localeCompare(b.label));
  const gridPos = new Map(iso.map((n, k) => [n.id, { x: -2.6 + 5.2 * (k % 60) / 59, y: -3.3 - 0.11 * Math.floor(k / 60) }]));
  for (const n of data.nodes) {
    const pos = gridPos.get(n.id) || { x: n.x, y: n.y };
    const size = isIsolated(n) ? 1.4 : 2 + 5.2 * Math.pow(Math.log1p(n.n_pubs) / Math.log1p(maxPubs), 1.15);
    g.addNode(n.id, { ...n, x: pos.x, y: pos.y, ox: pos.x, oy: pos.y, size, color: nodeColor(n) });
  }
  const units = (n) => (n.affiliations || []).filter(isUnit);
  state.hasLayer = {}; state.lensCount = {};
  for (const e of data.edges) {
    if (g.hasEdge(e.s, e.t)) continue;
    const ua = units(g.getNodeAttributes(e.s)), ub = units(g.getNodeAttributes(e.t));
    const a = { p: e.p, raw: e.raw, ev: e.ev || {}, conf: e.conf || {}, unexplored: e.unexplored, w: null,
                coTeach: !!(e.co_teach || ((e.ev || {}).teach || {}).shared && e.ev.teach.shared.length),
                cross: ua.length > 0 && ub.length > 0 && !ua.some((x) => ub.includes(x)) };
    g.addEdge(e.s, e.t, a);
    for (const l in e.p) if (l === "field" || e.raw[l] > 0) state.hasLayer[l] = true;
    for (const l of LENSES) { state.lens = l; if (l !== "all" && lensMatch(a)) state.lensCount[l] = (state.lensCount[l] || 0) + 1; }
  }
  for (const l of LENSES) state.lensCount[l] = state.lensCount[l] || 0;
  state.lens = "all";
  state.graph = g;

  document.getElementById("attribution").textContent = data.meta.attribution;
  document.getElementById("snapshot").textContent = data.meta.snapshot_date;
  document.getElementById("build").textContent = data.meta.build_date;

  // Show model and resolution switches when available in meta
  const hasModel = !!data.meta.alt_available;
  const hasRes = !!(data.meta.partitions && Object.keys(data.meta.partitions).length > 1);
  document.getElementById("model-row").hidden = !hasModel;
  document.getElementById("res-row").hidden = !hasRes;
  document.getElementById("advanced-group").hidden = !hasModel && !hasRes;

  const MIN_ZOOM_RATIO = 0.08, MAX_ZOOM_RATIO = 3.2;
  state.renderer = new SigmaClass(g, document.getElementById("graph"), {
    minCameraRatio: MIN_ZOOM_RATIO, maxCameraRatio: MAX_ZOOM_RATIO,
    enableEdgeEvents: true,
    renderEdgeLabels: false, labelRenderedSizeThreshold: 11, labelDensity: 0.35, labelGridCellSize: 110, defaultEdgeColor: EDGE_COLOR, minEdgeThickness: 0.5,
    labelColor: { color: DARK ? "#f5f5f7" : "#1d1d1f" }, labelSize: 12, labelWeight: "500",
    labelFont: "-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Inter', 'Segoe UI', system-ui, sans-serif",
    nodeReducer: (node, attrs) => {
      const v = state.view, member = v && v.members.has(node), partner = v && v.partners.has(node), inView = member || partner;
      if (v && v.single ? !inView : (isIsolated(attrs) && !state.showIsolated)) return { ...attrs, hidden: true };
      const base = nodeColor(attrs);
      const res = { ...attrs, size: Math.max(attrs.size, v && v.single ? 3.2 : 0) * state.nodeScale * (v && v.single ? 1.25 : 1), color: rgba(base, 0.92) };
      const dim = () => { res.color = rgba(DIM_HEX, DARK ? 0.35 : 0.34); res.label = ""; res.size *= 0.6; res.zIndex = 0; res.forceLabel = false; };
      if (v && !v.single && !inView) { res.color = rgbaMix(base, 0.78, 0.55); res.label = ""; res.size *= 0.55; res.zIndex = 0; }
      if (partner) { res.color = rgbaMix(base, 0.35, 0.95); res.size *= 0.85; }
      if (v && v.single && v.n <= 70) res.forceLabel = true;
      const sel = state.selected;
      if (sel) {
        if (node !== sel && !g.areNeighbors(node, sel)) dim();
        else if (node !== sel) res.forceLabel = true;
        if (node === sel) { res.highlighted = true; res.zIndex = 2; res.size *= 1.35; }
      } else if (state.bridgePath && state.bridgePath.includes(node)) {
        res.color = LENS_EDGE;
        res.forceLabel = true;
        res.zIndex = 3;
        res.size *= (node === state.bridgeA || node === state.bridgeB) ? 1.45 : 1.3;
      } else if (state.bridgeA && state.bridgeB) {
        res.color = rgbaMix(base, 0.55, 0.45);
        res.size *= 0.75;
        res.zIndex = 0;
        res.label = "";
      } else if (state.hoverNode && state.hoverT > 0.005) {
        const hn = state.hoverNode, ht = state.hoverT;
        if (node === hn) { res.zIndex = 2; res.size *= 1 + 0.35 * ht; }
        else if (g.areNeighbors(node, hn)) { res.zIndex = 1; res.size *= 1 + 0.1 * ht; }
        else { res.color = rgbaMix(base, 0.32 * ht, 1 - 0.2 * ht); res.size *= 1 - 0.06 * ht; res.zIndex = 0; if (ht > 0.4) res.label = ""; }
      }
      if (state.hoverPair && (node === state.hoverPair[0] || node === state.hoverPair[1])) {
        res.color = LENS_EDGE;
        res.forceLabel = true;
        res.zIndex = 4;
        res.size *= 1.35;
      }
      if (state.hoveredEdge && (node === g.source(state.hoveredEdge) || node === g.target(state.hoveredEdge))) {
        res.color = LENS_EDGE;
        res.forceLabel = true;
        res.zIndex = 4;
        res.size *= 1.3;
      }
      return res;
    },
    edgeReducer: (edge, attrs) => {
      const w = attrs.w || 0;
      const res = { ...attrs, hidden: !edgeVisible(edge, attrs), size: 0.45 + 1.0 * w, color: rgba2(EDGE_RGB, state.edgeAlpha * (0.6 + 0.8 * w)) };
      if (state.lens !== "all") { res.color = rgba(LENS_EDGE, 0.85); res.size = state.view && state.view.single ? 1.8 : 1.1; }
      const s = g.source(edge), tg = g.target(edge);
      if (state.selected) {
        if (s === state.selected || tg === state.selected) { res.color = HIGHLIGHT; res.size = 1.2 + 1.2 * w; res.zIndex = 1; }
      } else if (state.hoverNode && state.hoverT > 0.005) {
        const ht = state.hoverT;
        if (s === state.hoverNode || tg === state.hoverNode) { res.hidden = false; res.color = rgba(HIGHLIGHT, 0.15 + 0.7 * ht); res.size = 0.6 + (0.5 + w) * ht; res.zIndex = 1; }
        else res.color = rgba2(EDGE_RGB, state.edgeAlpha * (0.6 + 0.8 * w) * (1 - 0.45 * ht));
      }
      if (!state.selected && state.bridgeEdges && state.bridgeEdges.has(edge)) {
        res.hidden = false;
        res.color = LENS_EDGE;
        res.size = 2.6;
        res.zIndex = 3;
      }
      if (edge === state.hoverEdge || edge === state.hoveredEdge) {
        res.hidden = false;
        res.color = LENS_EDGE;
        res.size = 2.8;
        res.zIndex = 4;
      }
      return res;
    },
  });
  if (state.renderer.setSetting) state.renderer.setSetting("stagePadding", 64);
  const fitBox = () => state.renderer.setCustomBBox && state.renderer.setCustomBBox(
    state.showIsolated ? { x: [-2.8, 2.8], y: [-3.3 - 0.11 * Math.ceil(iso.length / 60), 2.8] } : { x: [-2.8, 2.8], y: [-2.8, 2.8] });
  fitBox();
  state.fitBox = fitBox;

  const tip = document.getElementById("tooltip"), graphEl = document.getElementById("graph");
  state.renderer.on("enterNode", ({ node }) => {
    state.hoveredEdge = null;
    graphEl.classList.add("hover-node");
    if (!state.selected) hoverTo(node);
    const n = g.getNodeAttributes(node);
    const more = (n.affiliations || []).filter((a) => a !== n.dept);
    tip.innerHTML = `<b>${esc(n.label)}</b><br>${esc(n.role || "")}${n.dept ? "<br>" + esc(n.dept) : ""}${more.length ? "<br><i>+ " + esc(more.join("; ")) + "</i>" : ""}<br>${n.n_pubs} ${t("pubs")}`;
    tip.classList.add("show");
  });
  state.renderer.on("leaveNode", () => {
    graphEl.classList.remove("hover-node");
    tip.classList.remove("show");
    if (state.hoverNode) hoverTo(null);
  });
  state.renderer.on("enterEdge", ({ edge }) => {
    if (state.hoverNode) return;
    const focused = !!(state.selected || (state.view && state.view.single) || state.lens !== "all" || (state.bridgeEdges && state.bridgeEdges.has(edge)));
    if (!focused) return;
    const a = g.getEdgeAttributes(edge);
    if (!edgeVisible(edge, a)) return;
    state.hoveredEdge = edge;
    graphEl.classList.add("hover-node");
    const s = g.getNodeAttributes(g.source(edge)), tg = g.getNodeAttributes(g.target(edge));
    const why = pairWhy(a);
    tip.innerHTML = `<b>${esc(s.label)} ↔ ${esc(tg.label)}</b>` +
      `<br><small>${esc(shortUnit(s.dept) || "—")} · ${esc(shortUnit(tg.dept) || "—")}</small>` +
      `<br>${topLayersText(a)}` +
      (why ? `<br><i>${why}</i>` : "");
    tip.classList.add("show");
    state.renderer.refresh();
  });
  state.renderer.on("leaveEdge", () => {
    if (!state.hoveredEdge) return;
    state.hoveredEdge = null;
    if (!state.hoverNode) {
      graphEl.classList.remove("hover-node");
      tip.classList.remove("show");
    }
    state.renderer.refresh();
  });
  state.renderer.on("clickNode", ({ node }) => {
    const bd = document.getElementById("bridge-details");
    if (!state.selected && bd && bd.open && state.tab === "explore" && state.bridgePickSlot) {
      if (state.bridgePickSlot === "a") {
        setBridgePair(node, state.bridgeB, state.bridgeB ? null : "b");
      } else if (state.bridgePickSlot === "b" && state.bridgeA !== node) {
        setBridgePair(state.bridgeA, node, null);
      }
      return;
    }
    select(node, true);
  });
  state.renderer.on("clickStage", () => {
    if (state.selected) select(null);
  });

  const structCount = new Map();
  for (const n of data.nodes) for (const a of n.affiliations || []) structCount.set(a, (structCount.get(a) || 0) + 1);
  const all = [...structCount].sort((a, b) => b[1] - a[1]);
  state.structIndex = new Map(all.map(([a], i) => [a, i]));
  state.structs = all.filter(([a, c]) => c >= 3 && isUnit(a));
  updateStatsText();

  const cam = state.renderer.getCamera();
  const zin = document.getElementById("zoom-in"), zout = document.getElementById("zoom-out");
  const syncZoomBtns = () => {
    zin.disabled = cam.ratio <= MIN_ZOOM_RATIO * 1.03;
    zout.disabled = cam.ratio >= MAX_ZOOM_RATIO * 0.97;
  };
  cam.on("updated", syncZoomBtns);
  syncZoomBtns();
  zin.onclick = () => { if (!zin.disabled) cam.animatedZoom({ duration: 200, factor: 1.35 }); };
  zout.onclick = () => { if (!zout.disabled) cam.animatedUnzoom({ duration: 200, factor: 1.35 }); };
  document.getElementById("zoom-reset").onclick = () => cam.animatedReset({ duration: 350 });

  applyI18n();
  recompute();
  if (!isSwitch && location.hash.length > 1) readHash();
  const ws = []; g.forEachEdge((e, a) => { if (a.w !== null) ws.push(a.w); });
  ws.sort((a, b) => b - a);
  const cap = DARK ? 3500 : 5000;
  const thr = document.getElementById("threshold");
  if (ws.length > cap) {
    state.defaultThreshold = Math.min(0.95, Math.max(0.55, Math.ceil(ws[cap] * 100) / 100));
    if (!isSwitch) {
      state.threshold = state.defaultThreshold;
      thr.value = state.threshold;
      document.getElementById("threshold-out").textContent = state.threshold.toFixed(2);
    }
    state.renderer.refresh();
  }
}

function exportGraphPng() {
  if (!state.renderer) return;
  if (state.renderer.render) state.renderer.render();
  const wrap = document.getElementById("graph");
  const canvases = wrap ? wrap.querySelectorAll("canvas") : [];
  if (!canvases.length) return;
  const w = canvases[0].width, h = canvases[0].height;
  const out = document.createElement("canvas");
  out.width = w;
  out.height = h;
  const ctx = out.getContext("2d");
  ctx.fillStyle = BG_HEX;
  ctx.fillRect(0, 0, w, h);
  canvases.forEach((c) => {
    try { ctx.drawImage(c, 0, 0); } catch {}
  });
  const dpr = window.devicePixelRatio || 1;
  ctx.font = `500 ${Math.round(12 * dpr)}px -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Inter', sans-serif`;
  ctx.fillStyle = DARK ? "rgba(245,245,247,0.68)" : "rgba(29,29,31,0.68)";
  ctx.fillText("Embedded Researcher · Università di Trento", Math.round(18 * dpr), h - Math.round(16 * dpr));
  const a = document.createElement("a");
  a.download = "embedded-researcher-unitn.png";
  a.href = out.toDataURL("image/png");
  a.click();
  const btn = document.getElementById("export-png");
  if (btn) {
    btn.classList.add("flash-ok");
    setTimeout(() => btn.classList.remove("flash-ok"), 950);
  }
}

// Global UI bindings (bound once)
applyTheme(state.theme, false);
if (window.matchMedia) {
  const mq = window.matchMedia("(prefers-color-scheme: dark)");
  if (mq.addEventListener) {
    mq.addEventListener("change", (ev) => {
      try { if (localStorage.getItem("theme")) return; } catch {}
      applyTheme(ev.matches ? "dark" : "light", false);
    });
  }
}
document.getElementById("theme-toggle").onclick = () => applyTheme(state.theme === "dark" ? "light" : "dark", true);
document.querySelectorAll("#theme-switch button").forEach((b) => {
  b.onclick = () => applyTheme(b.dataset.themeVal, true);
});
const exportPngBtn = document.getElementById("export-png");
if (exportPngBtn) exportPngBtn.onclick = exportGraphPng;
const shareBtn = document.getElementById("share-btn");
if (shareBtn) {
  shareBtn.onclick = () => {
    writeHash();
    const url = window.location.href;
    const done = () => {
      shareBtn.classList.add("flash-ok");
      setTimeout(() => shareBtn.classList.remove("flash-ok"), 950);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url).then(done).catch(done);
    } else {
      done();
    }
  };
}
const graphCanvasWrap = document.getElementById("graph");
graphCanvasWrap.addEventListener("mousedown", () => graphCanvasWrap.classList.add("dragging"));
window.addEventListener("mouseup", () => graphCanvasWrap.classList.remove("dragging"));
graphCanvasWrap.addEventListener("mousemove", (ev) => {
  const tip = document.getElementById("tooltip");
  const r = ev.currentTarget.getBoundingClientRect();
  tip.style.left = Math.min(ev.clientX - r.left + 14, r.width - 230) + "px";
  tip.style.top = (ev.clientY - r.top + 14) + "px";
});
document.getElementById("matrix-open").onclick = openMatrix;
const aboutOpenBtn = document.getElementById("about-open");
if (aboutOpenBtn) aboutOpenBtn.onclick = openAbout;
document.getElementById("panel-back").onclick = () => select(null);
document.getElementById("panel-print").onclick = () => window.print();
const panelBridgeBtn = document.getElementById("panel-bridge-btn");
if (panelBridgeBtn) {
  panelBridgeBtn.onclick = () => {
    const me = state.selected;
    select(null);
    setTab("explore");
    const bd = document.getElementById("bridge-details");
    if (bd) bd.open = true;
    setBridgePair(me, null);
    const inB = document.getElementById("bridge-input-b");
    if (inB) setTimeout(() => inB.focus(), 50);
  };
}
document.querySelectorAll("#side-tabs button").forEach((b) => { b.onclick = () => setTab(b.dataset.tab); });
document.querySelectorAll("#legend-mode button").forEach((b) => {
  b.onclick = () => { state.legendMode = b.dataset.mode; buildLegend(); };
});
document.getElementById("legend-filter").oninput = (ev) => { state.legendQuery = ev.target.value; buildLegend(); };
document.querySelectorAll("#model-switch button").forEach((b) => { b.onclick = () => switchModel(b.dataset.model); });
document.querySelectorAll("#res-switch button").forEach((b) => { b.onclick = () => applyResolution(b.dataset.res); });
document.querySelectorAll("#color-by button").forEach((b) => {
  b.onclick = () => {
    state.colorBy = b.dataset.value;
    syncColorByButtons();
    buildLegend();
    if (state.renderer) state.renderer.refresh();
  };
});
document.getElementById("view-dept").onchange = (ev) => setStruct(ev.target.value);
document.getElementById("view-comm").onchange = (ev) => setFocus(ev.target.value);
const nsEl = document.getElementById("node-size"), eoEl = document.getElementById("edge-opacity"), thrEl = document.getElementById("threshold");
nsEl.value = state.nodeScale; document.getElementById("node-size-out").textContent = state.nodeScale.toFixed(2);
eoEl.value = state.edgeAlpha; document.getElementById("edge-opacity-out").textContent = state.edgeAlpha.toFixed(2);
thrEl.value = state.threshold; document.getElementById("threshold-out").textContent = state.threshold.toFixed(2);
nsEl.oninput = () => { state.nodeScale = +nsEl.value; document.getElementById("node-size-out").textContent = (+nsEl.value).toFixed(2); if (state.renderer) state.renderer.refresh(); };
eoEl.oninput = () => { state.userModifiedEdgeAlpha = true; state.edgeAlpha = +eoEl.value; document.getElementById("edge-opacity-out").textContent = (+eoEl.value).toFixed(2); if (state.renderer) state.renderer.refresh(); };
thrEl.oninput = () => { state.threshold = +thrEl.value; document.getElementById("threshold-out").textContent = (+thrEl.value).toFixed(2); if (state.renderer) state.renderer.refresh(); };
document.getElementById("show-isolated").onchange = (ev) => {
  state.showIsolated = ev.target.checked; if (state.fitBox) state.fitBox(); if (state.renderer) state.renderer.refresh();
  if (state.showIsolated && state.renderer) state.renderer.getCamera().animatedReset({ duration: 400 });
};
document.getElementById("use-conf").onchange = (ev) => { state.useConf = ev.target.checked; recompute(true); };
document.getElementById("reset-appearance").onclick = (ev) => {
  state.colorBy = "community";
  state.threshold = state.defaultThreshold;
  state.userModifiedEdgeAlpha = false;
  state.edgeAlpha = state.defaultEdgeAlpha;
  state.nodeScale = 1;
  state.showIsolated = false;
  thrEl.value = state.threshold; document.getElementById("threshold-out").textContent = state.threshold.toFixed(2);
  eoEl.value = state.edgeAlpha; document.getElementById("edge-opacity-out").textContent = state.edgeAlpha.toFixed(2);
  nsEl.value = state.nodeScale; document.getElementById("node-size-out").textContent = state.nodeScale.toFixed(2);
  document.getElementById("show-isolated").checked = false;
  syncColorByButtons();
  if (state.fitBox) state.fitBox();
  buildLegend();
  if (state.renderer) state.renderer.refresh();
  flashButton(ev.currentTarget);
};
document.getElementById("reset").onclick = (ev) => {
  if (!state.data) return;
  for (const l of state.data.meta.layers) {
    state.weights[l] = state.defaultWeights[l] !== undefined ? state.defaultWeights[l] : Number(state.data.meta.weights[l]);
    state.enabled[l] = true;
  }
  state.useConf = false;
  const uc = document.getElementById("use-conf");
  if (uc) uc.checked = false;
  buildWeights();
  recompute(true);
  buildExplore();
  flashButton(ev.currentTarget);
};
document.getElementById("lang").onclick = () => { state.lang = state.lang === "it" ? "en" : "it"; try { localStorage.setItem("lang", state.lang); } catch {} applyI18n(); };
document.addEventListener("keydown", (ev) => {
  const search = document.getElementById("search");
  const typing = ["INPUT", "SELECT", "TEXTAREA"].includes(document.activeElement && document.activeElement.tagName);
  if (ev.key === "/" && !typing) { ev.preventDefault(); search.focus(); search.select(); }
  else if (ev.key === "Escape") {
    if (!document.getElementById("matrix").hidden) { closeMatrix(); return; }
    if (!document.getElementById("about").hidden) { closeAbout(); return; }
    closeCustomSelects();
    search.blur();
    if (state.selected) { select(null); return; }
    if (state.bridgeA || state.bridgeB) { setBridgePair(null, null); return; }
    state.focus = null; state.lens = "all"; buildLenses(); renderChips(); setStruct("");
  }
});
setupSearch();
setupBridgeFinder();
setupCustomSelects();
setupTooltips();

function closeCustomSelects() {
  document.querySelectorAll(".cselect").forEach((box) => {
    box.classList.remove("open");
    const btn = box.querySelector(".cselect-btn"), menu = box.querySelector(".dropdown-menu");
    if (btn) btn.setAttribute("aria-expanded", "false");
    if (menu) menu.hidden = true;
  });
}

function setupCustomSelects() {
  document.querySelectorAll(".cselect").forEach((box) => {
    const btn = box.querySelector(".cselect-btn"), menu = box.querySelector(".dropdown-menu");
    if (!btn || !menu) return;
    box.onclick = (ev) => {
      if (ev.target.closest(".dropdown-menu")) return;
      ev.stopPropagation();
      const wasOpen = !menu.hidden;
      closeCustomSelects();
      if (!wasOpen) {
        box.classList.add("open");
        btn.setAttribute("aria-expanded", "true");
        menu.hidden = false;
      }
    };
  });
  document.addEventListener("click", (ev) => {
    if (!ev.target.closest(".cselect")) closeCustomSelects();
  });
}

function setupTooltips() {
  const tip = document.getElementById("ui-tip");
  if (!tip) return;
  let timer = 0, currentEl = null, lastX = 0;
  const hide = () => {
    if (timer) { clearTimeout(timer); timer = 0; }
    currentEl = null;
    tip.hidden = true;
  };
  const show = (el) => {
    const text = el.dataset.tip;
    if (!text) return;
    tip.textContent = text;
    tip.hidden = false;
    const rect = el.getBoundingClientRect(), tr = tip.getBoundingClientRect();
    let left = Math.min(Math.max(10, lastX - tr.width / 2), window.innerWidth - tr.width - 10);
    let top = rect.bottom + 8;
    if (top + tr.height > window.innerHeight - 10) top = Math.max(10, rect.top - tr.height - 8);
    tip.style.left = `${Math.round(left)}px`;
    tip.style.top = `${Math.round(top)}px`;
  };
  document.addEventListener("mousemove", (ev) => {
    lastX = ev.clientX;
    const el = ev.target.closest && ev.target.closest("[data-tip]");
    if (!el || !el.dataset.tip || (el.classList && el.classList.contains("open"))) {
      if (currentEl) hide();
      return;
    }
    if (el === currentEl) return;
    hide();
    currentEl = el;
    timer = setTimeout(() => show(el), 380);
  });
  document.addEventListener("mousedown", hide);
  document.addEventListener("scroll", hide, true);
}

function setupBuildCard(fallbackMsg) {
  const box = document.getElementById("loading"), card = document.getElementById("build-card");
  const spin = document.getElementById("loading-spinner"), ltxt = document.getElementById("loading-text");
  const btn = document.getElementById("build-start-btn"), altCb = document.getElementById("build-alt-cb");
  const wrap = document.getElementById("build-status-wrap"), bar = document.getElementById("build-bar");
  const stepTxt = document.getElementById("build-step-text"), logPre = document.getElementById("build-log");
  applyI18n();
  fetch("/api/status")
    .then((r) => { if (!r.ok) throw new Error(r.statusText); return r.json(); })
    .then((st) => {
      if (spin) spin.hidden = true;
      if (ltxt) ltxt.hidden = true;
      if (card) card.hidden = false;
      let pollTimer = 0;
      const poll = () => {
        fetch("/api/status")
          .then((r) => r.json())
          .then((s) => {
            if (s.building || s.step_index > 0 || s.error) {
              wrap.hidden = false;
              const pct = s.total_steps ? Math.round((s.step_index / s.total_steps) * 100) : 5;
              bar.style.width = `${Math.max(4, pct)}%`;
              stepTxt.textContent = s.error ? `Errore: ${s.error}` : (s.current_step ? `${t("build_running")} (${s.step_index}/${s.total_steps}: ${s.current_step})` : t("build_running"));
              if (s.logs && s.logs.length) {
                logPre.textContent = s.logs.slice(-20).join("\n");
                logPre.scrollTop = logPre.scrollHeight;
              }
            }
            if (!s.building && s.has_graph && !s.error) {
              if (pollTimer) clearInterval(pollTimer);
              fetch("graph.json")
                .then((r) => r.json())
                .then(init)
                .then(() => { card.hidden = true; box.classList.add("done"); });
            } else if (!s.building && s.error) {
              if (pollTimer) clearInterval(pollTimer);
              btn.disabled = false;
            }
          })
          .catch(() => {});
      };
      if (st.building) {
        btn.disabled = true;
        wrap.hidden = false;
        poll();
        pollTimer = setInterval(poll, 1200);
      }
      btn.onclick = () => {
        btn.disabled = true;
        wrap.hidden = false;
        stepTxt.textContent = t("build_running");
        fetch("/api/build", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-Unitn-Net": "1" },
          body: JSON.stringify({ alt: !!(altCb && altCb.checked) }),
        })
          .then((r) => r.json())
          .then(() => {
            if (pollTimer) clearInterval(pollTimer);
            poll();
            pollTimer = setInterval(poll, 1200);
          })
          .catch((e) => {
            stepTxt.textContent = String(e);
            btn.disabled = false;
          });
      };
    })
    .catch(() => {
      document.getElementById("intro").querySelector("p").textContent = fallbackMsg;
      box.classList.add("error");
      if (ltxt) ltxt.textContent = fallbackMsg;
    });
}

document.getElementById("intro").querySelector("p").textContent = t("loading");
document.getElementById("loading-text").textContent = t("loading");
fetch("graph.json")
  .then((r) => { if (!r.ok) throw new Error(r.statusText); return r.json(); })
  .then(init)
  .then(() => document.getElementById("loading").classList.add("done"))
  .catch((err) => {
    const msg = `${t("load_error")} (${err.message})`;
    setupBuildCard(msg);
  });
