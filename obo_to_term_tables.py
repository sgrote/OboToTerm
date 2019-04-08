#!/usr/bin/python3

import argparse

import obo_to_term_functions as T


parser = argparse.ArgumentParser(description='Convert obo to term.txt, term2term.txt and graph_path.txt', usage='./obo_to_term.py po.obo .')
# mandatory
parser.add_argument("obofile", help="Ontology in obo-format")
parser.add_argument("outdir", help="directory where term.txt, term2term.txt and graph_path.txt are written to")
# optional
parser.add_argument("-r", "--root_nodes", default="molecular_function,biological_process,cellular_component", help="Comma separated string of domains/namespaces")

args = parser.parse_args()


###

# get root nodes
root_nodes = args.root_nodes.split(",")
if len(root_nodes) == 1:
	default_namespace = root_nodes[0]
else:
	default_namespace = "all"


# write term.txt, get IDs and root IDs
ids, root_ids = T.obo_to_term(args.obofile, args.outdir, root_nodes, default_namespace)

# write term2term.txt, get {parent:[child1, child2]} for distance-1-relationships
parents = T.obo_to_term2term(args.obofile, args.outdir, ids)

# write graph_path.txt with all relationships
T.graph_path(args.outdir, root_ids, parents)

