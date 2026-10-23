-- Preços diários de todos os ativos analisados, num formato único (ativo, data, preco).
-- Ações usam o fechamento ajustado por proventos; o dólar do BCB entra como ativo próprio.
--
-- Correção de data das moedas do Yahoo (tickers "=X"): o candle diário com data D tem
-- fechamento ≈ abertura ≈ cotação por volta de 00h em Londres, ou seja, o fechamento do
-- pregão ANTERIOR. Cada valor é atribuído à data útil anterior da própria série (ver
-- DECISOES.md: a série corrigida tem correlação 0,96 com o fechamento das 17h de Brasília
-- calculado a partir das barras de 1h; a original, 0,22 com o dólar do BCB).
with yahoo_bruto as (
    select
        ticker as ativo,
        cast(data as date) as data_original,
        coalesce(fechamento_ajustado, fechamento) as preco
    from {{ source('bruto', 'yahoo_diario') }}
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
)

select * from yahoo where preco > 0 and data is not null
union all
select * from bcb where preco > 0
