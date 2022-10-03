import itertools
import logging
import json

from .index import Index
from .workload import Column, Table

def candidates_per_query(workload, max_index_width, candidate_generator):
    candidates = []

    for query in workload.queries:
        candidates.append(candidate_generator(query, max_index_width))

    return candidates


def syntactically_relevant_indexes(query, max_index_width):
    # "SAEFIS" or "BFI" see paper linked in DB2Advis algorithm
    # This implementation is "BFI" and uses all syntactically relevant indexes.
    columns = query.columns
    logging.debug(f"{query}")
    logging.debug(f"Indexable columns: {len(columns)}")

    indexable_columns_per_table = {}
    for column in columns:
        if column.table not in indexable_columns_per_table:
            indexable_columns_per_table[column.table] = set()
        indexable_columns_per_table[column.table].add(column)

    possible_column_combinations = set()
    for table in indexable_columns_per_table:
        columns = indexable_columns_per_table[table]
        for index_length in range(1, max_index_width + 1):
            possible_column_combinations |= set(
                itertools.permutations(columns, index_length)
            )

    logging.debug(f"Potential indexes: {len(possible_column_combinations)}")
    return [Index(p) for p in possible_column_combinations]

def parse_candidates(candidate_file, max_width):
    tables = {}
    cols = {}
    cands = []

    with open(candidate_file) as cfile:
        candstrs = [conf.split(" on ")[1] for conf in json.load(cfile).keys() if "Index" in conf]
    for cand in candstrs:
        parsed = cand[:-1].split('(')
        tablestr = parsed[0]
        colstrs = parsed[1].split(',')

        if len(colstrs) > max_width:
            continue

        if tablestr not in tables:
            tables[tablestr] = Table(tablestr)
        for colstr in colstrs:
            if colstr not in cols:
                cols[colstr] = Column(colstr)
                tables[tablestr].add_column(cols[colstr])

        cands.append(Index([cols[col] for col in colstrs]))
    return set(cands)



def make_filtered_gen(cand_file, width):
    candidates = parse_candidates(cand_file, width)
    return lambda q, w: [i for i in syntactically_relevant_indexes(q,w) if i in candidates]
