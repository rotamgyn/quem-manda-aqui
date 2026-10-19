// Espelha o contrato de dados gerado por modulos/eleicoes-2026/pipeline (exportar.py).
// `null` onde o JSON pode trazer null.

export type Cargo = 'presidente' | 'governador';
export type Situacao = 'eleito' | '2º turno' | 'não eleito' | '';

export type VotoCandidato = {
  numero: number;
  nome_urna: string;
  partido: string;
  votos: number;
  situacao: Situacao;
  /** % dos votos válidos; null quando não há votos válidos. */
  pct: number | null;
};

export type Resultado = {
  ano: number;
  turno: number;
  cargo: Cargo;
  uf: string;
  municipio_tse: string | null;
  aptos: number;
  comparecimento: number;
  abstencao: number;
  brancos: number;
  nulos: number;
  validos: number;
  pct_secoes_totalizadas: number;
  /** Candidatos válidos (percentuais sobre `validos`). */
  candidatos: VotoCandidato[];
  /** Candidatos com votos anulados (inclusive sub judice): fora de `validos`, sem `pct`. */
  anulados: Omit<VotoCandidato, 'pct'>[];
  votos_anulados: number;
};

export type LinhaPartido = {
  partido: string;
  pct_2022: number | null;
  pct_2026: number | null;
  delta_pp: number | null;
  /** Siglas originais de 2022 somadas nesta linha (ex.: PRD ← PATRIOTA + PTB); [] sem 2022. */
  siglas_2022: string[];
};

export type Comparacao = {
  cargo: Cargo;
  uf: string;
  municipio_tse: string | null;
  r2022: Resultado | null;
  r2026: Resultado | null;
  partidos: LinhaPartido[];
  volatilidade: number | null;
  vencedor_2022: string | null;
  vencedor_2026: string | null;
  virou: boolean | null;
  apuracao_completa: boolean;
  /** Só nas comparações de abrangência (BR, UF), não nas de município. */
  nome?: string;
};

export type MunicipioComparado = {
  tse: string;
  ibge: string;
  nome: string;
  slug: string;
  capital: boolean;
  presidente: Comparacao;
  /** Ausente nas cidades do exterior (UF ZZ). */
  governador?: Comparacao;
};

export type ItemRanking = {
  tse: string;
  nome: string;
  uf: string;
  slug: string;
  aptos: number;
  volatilidade: number;
  vencedor_2022: string | null;
  vencedor_2026: string | null;
  virou: boolean | null;
};

export type Meta = { gerado_em: string; fonte_2026_dg_hg: string; pct_secoes_br: number };
