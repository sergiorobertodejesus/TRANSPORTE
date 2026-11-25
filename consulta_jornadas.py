"""Consulta compartilhada das jornadas operacionais."""

from periodo_operacional import limites_operacionais


def consultar_jornadas(db, dia):
    inicio, fim = limites_operacionais(dia)

    jornadas = db.execute("""
        SELECT
            j.id,
            j.motorista_id,
            j.veiculo_id,
            m.nome AS motorista,
            v.nome AS veiculo,
            v.placa,
            j.data_inicio,
            j.data_fim,
            j.km_inicial,
            j.km_final,
            COALESCE(g.bruto, 0) AS bruto,
            COALESCE(d.despesas, 0) AS despesas,
            COALESCE(d.recarga, 0) AS recarga,
            COALESCE(d.combustivel, 0) AS combustivel
        FROM jornadas j
        JOIN motoristas m ON m.id = j.motorista_id
        JOIN veiculos v ON v.id = j.veiculo_id
        LEFT JOIN (
            SELECT jornada_id,
                SUM(
                    COALESCE(uber_total, 0)
                    + COALESCE(noventa_nove_total, 0)
                    + COALESCE(corridas_particulares, 0)
                ) AS bruto
            FROM ganhos
            GROUP BY jornada_id
        ) g ON g.jornada_id = j.id
        LEFT JOIN (
            SELECT jornada_id,
                SUM(valor) AS despesas,
                SUM(CASE
                    WHEN categoria = 'Recarga elétrica'
                    THEN valor ELSE 0
                END) AS recarga,
                SUM(CASE
                    WHEN categoria = 'Combustível'
                    THEN valor ELSE 0
                END) AS combustivel
            FROM despesas
            GROUP BY jornada_id
        ) d ON d.jornada_id = j.id
        WHERE j.status = 'ENCERRADA'
          AND julianday(j.data_fim) >= julianday(?)
          AND julianday(j.data_fim) < julianday(?)
        ORDER BY j.id
    """, (inicio.isoformat(), fim.isoformat())).fetchall()

    return jornadas
