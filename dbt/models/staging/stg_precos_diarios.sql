-- Preços diários de todos os ativos analisados, num formato único (ativo, data, preco).
-- Ações usam o fechamento ajustado por proventos; o dólar do BCB entra como ativo próprio.
--
-- Correção de data das moedas do Yahoo (tickers "=X"): o candle diário com data D tem
-- fechamento ≈ abertura ≈ cotação por volta de 00h em Londres, ou seja, o fechamento do
-- pregão ANTERIOR. Cada valor é atribuído à data útil anterior da própria série (ver
-- DECISOES.md: a série corrigida tem correlação 0,96 com o fechamento das 17h de Brasília
-- calculado a partir das barras de 1h; a original, 0,22 com o dólar do BCB).
--
-- Picos isolados: um preço que se afasta mais de 30% (em log) dos dois vizinhos e volta no
-- pregão seguinte é erro de dado (ex.: COP=X em 2014–2016 alterna 2.399 e 24,25, vírgula
-- deslocada) e é descartado. Movimentos reais grandes não revertem no dia seguinte.
with yahoo_lido as (
    select
        ticker as ativo,
        cast(data as date) as data_original,
        coalesce(fechamento_ajustado, fechamento) as preco
    from {{ source('bruto', 'yahoo_diario') }}
    where coalesce(fechamento_ajustado, fechamento) > 0
),

yahoo_vizinhos as (
    select
        *,
        ln(preco / lag(preco) over w) as r_antes,
        ln(lead(preco) over w / preco) as r_depois
    from yahoo_lido
    window w as (partition by ativo order by data_original)
),

yahoo_bruto as (
    select ativo, data_original, preco
    from yahoo_vizinhos
    where not (abs(r_antes) > {{ var('limite_pico_isolado') }}
               and abs(r_depois) > {{ var('limite_pico_isolado') }}
               and sign(r_antes) <> sign(r_depois))
       or r_antes is null or r_depois is null
),

yahoo as (
    select
        ativo,
        case
            when ativo like '%=X'
                then lag(data_original) over (partition by ativo order by data_original)
            else data_original
        end as data,
        preco,
        'yahoo' as fonte
    from yahoo_bruto
),

bcb as (
    select
        'BCB_DOLAR' as ativo,
        cast(data as date) as data,
        valor as preco,
        'bcb_sgs' as fonte
    from {{ source('bruto', 'bcb_sgs') }}
    where serie_nome = 'dolar_venda'
),

yahoo_validos as (
    select * from yahoo where preco > 0 and data is not null
),

-- Carteiras long-short (comprada em ativo_long, vendida em ativo_short): o "preço" é a razão
-- P_long / P_short, cujo log-retorno é r_long − r_short entre dois pregões com os dois preços
long_short as (
    select c.carteira as ativo, l.data, l.preco / s.preco as preco, 'carteira' as fonte
    from {{ ref('carteiras') }} c
    join yahoo_validos l on l.ativo = c.ativo_long
    join yahoo_validos s on s.ativo = c.ativo_short and s.data = l.data
)

select * from yahoo_validos
union all
select * from bcb where preco > 0
union all
select * from long_short
