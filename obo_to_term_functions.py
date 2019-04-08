#!/usr/bin/python3


import sys
import copy



# 1) get term-ids (term.txt)

#> head(term_adult)
  #id               name term_type        acc is_obsolete is_root is_relation
#1  1            part_of  Relation Allen:4000           0       0           1
#2  2           Br_Brain     Brain Allen:4005           0       1           0
#3  3     GM_Grey Matter     Brain Allen:4006           0       0           0
#4  4  Tel_Telencephalon     Brain Allen:4007           0       0           0
#5  5 Cx_Cerebral Cortex     Brain Allen:4008           0       0           0
#6  6    FL_Frontal Lobe     Brain Allen:4009           0       0           0

# term_type = The ontology or namespace to which this term belongs (Example: biological_process)

def obo_to_term(obofile, outdir, root_nodes, default_namespace):
	'''
	Go through obofile, create term.txt, store term IDs
	@param obofile: ontology in obo-format
	@param outdir: directory where term.txt will be written to
	@param root_nodes: comma-separated string of root node names
	@param default_namespace: default namespace if not defined in obofile
	@return: {GO-ID: term-ID} , [IDs of root_nodes] 
	'''
		
	sys.stdout.write("Creating " + outdir + "/term.txt...\n")
	ids = {} # GO-ID: term-ID
	root_ids = []  # Ids for root_nodes names
	name = ""
	namespace = default_namespace
	with open(obofile, "r") as obo, open(outdir + "/term.txt", "w") as term:
		# is_a is a special case not part of onto-obo, other relations are there as terms
		term.write('\t'.join(["1", "is_a", "relationship", "is_a", "0", "0", "1"]) + "\n")
		ids["is_a"] = 1
		print(ids)
		# parse all other terms
		i = 2
		for line in obo:
			line = line.rstrip()
			# start of new entry
			if line.startswith("id:"):
				term_id = line[4:]
			elif line.startswith("name:"):
				name = line[6:]
			elif line.startswith("namespace:"):
				namespace = line[11:]
			# empty line after each entry, also after last
			elif len(line)==0 and name != "":
				if name in root_nodes:
					outline = [str(i), name, namespace, term_id, "0","1","0"]
					root_ids.append(i)
					print("Found root node:")
					print("\t".join(outline))
				elif name.startswith("obsolete"):
					outline = [str(i), name, namespace, term_id, "1","0","0"]
				else:
					outline = [str(i), name, namespace, term_id, "0","0","0"]
				term.write("\t".join(outline) + "\n")
				# save in dict for term2term.txt
				ids[term_id] = i
				namespace = default_namespace
				i += 1
	# check for root
	if len(root_ids) == 0:
		sys.stderr.write("Error: No root_nodes found.\n")
		sys.stderr.write("root_nodes searched for: " + ", ".join(root_nodes) + "\n")
		sys.exit("If " + obofile + " has different root_nodes, please specify them as --root_nodes")
	return ids, root_ids




# 2) get 1-distance-relationships (term2term.txt)

  #id relationship_type_ID parent child complete
#1  1                    1      2     3        0
#2  2                    1      3     4        0
#3  3                    1      4     5        0
#4  4                    1      5     6        0
#5  5                    1      6     7        0
#6  6                    1      7     8        0

def obo_to_term2term(obofile, outdir, ids):
	'''
	Go through obofile, create term2term.txt, store relationships
	@param obofile: ontology in obo-format
	@param outdir: directory where term.txt will be written to
	@param ids: {GO-ID: term-ID} created by obo_to_term()
	@return: {parent: [child1, child2]}
	'''

	sys.stdout.write("Creating " + outdir + "/term2term.txt...\n")
	parents = {} # {parent: [child1, child2]}
	with open(obofile, "r") as obo, open(outdir + "/term2term.txt", "w") as term2term:
		i = 1
		for line in obo:
			line = line.rstrip()
			if line.startswith("id:"):
				child = line[4:]
				child_id = ids[child]
			elif line.startswith("is_a:") or line.startswith("relationship:"):
				fields = line.split(" ")
				# is_a: GO:1903047 ! mitotic cell cycle process
				if fields[0] == "is_a:":
					relation = "is_a"
					parent = fields[1]
				# relationship: part_of GO:0000086 ! G2/M transition of mitotic cell cycle
				elif fields[0] == "relationship:":
					relation = fields[1]
					parent = fields[2]
				# IDs for relation and parent
				relation_id = ids[relation]
				parent_id = ids[parent]
				# write relation to file (same name can have multiple parents)
				outline = [str(i), str(relation_id), str(parent_id), str(child_id), "0"]
				term2term.write("\t".join(outline) + "\n")
				# add to parents dict for graph_path.txt
				if parent_id in parents:
					parents[parent_id].append(child_id)
				else:
					parents[parent_id] = [child_id]
				i += 1
	return parents




# 3) get graph-path

#> head(graph_path_adult)
  #id term1_id term2_id relationship_type_id distance relation_distance
#1  1        2        2                    1        0                 0
#2  2        2        3                    1        1                 1
#3  3        3        3                    1        0                 0
#4  4        2        4                    1        2                 2
#5  5        3        4                    1        1                 1
#6  6        4        4                    1        0                 0

# all paths parent->child with distances

def graph_path (outdir, root_ids, parents):
	'''
	Create graph_path.txt
	@param outdir: directory where term.txt will be written to
	@param root_ids: [IDs of root_nodes]
	@param: parents: {parent: [child1, child2]}
	'''
	sys.stdout.write("Collect all paths...\n")
	all_paths = []
	for r in root_ids:
		get_all_paths(parents, r, [], all_paths)
	dists = get_all_dists(all_paths)
	sys.stdout.write("Creating " + outdir + "/graph_path.txt...\n")
	with open(outdir + "/graph_path.txt", "w") as graph_path:
		idn = 1
		for d in dists:
			d = list(d)
			out = "\t".join(map(str, [idn] + d[:2] + ["1"] + [d[2]] + [d[2]]))
			graph_path.write(out + "\n")		
			idn += 1




def get_all_paths(pdict, parent, childlist, all_paths):
	'''
	recursively modify empty list "all_paths" to get a list of lists
	for all paths root -> node in graph pdict
	@param: pdict: {parent:[child1, child2]}
	@param: parent: root-id
	@param: childlist: [] to be recursively filled with one path root -> leave
	@param: all_paths: [] to be recursively filled with all paths root -> node
	'''
	childlist.append(parent)
	all_paths.append(childlist)
	if parent in pdict.keys():
		children = pdict[parent]
		for i in range(len(children)):
			new_childlist = copy.deepcopy(childlist)
			get_all_paths(pdict, children[i], new_childlist, all_paths)
	return None

''' test

#      A
#     / \
#    B   C
#   /|\ / 
#  D E F

pdict = {"A":["B", "C"], "B":["D","E","F"], "C":["F"]}
childlist = []
all_paths = []
get_all_paths(pdict, "A", childlist, all_paths)
all_paths == [['A'],['A','B'],['A','B','D'],['A','B','E'],['A','B','F'],['A','C'],['A','C','F']]

'''



def get_all_dists(all_paths):
	'''
	get a set of all paths (parent, child, dist)
	this removes duplicate entries due to multiple paths of same length
	@param: all_paths: list of lists for all paths root -> node
	@return: list of sets of all paths node -> node with distance
	'''
	all_dists = set()
	for p in all_paths:
		child = p[len(p)-1]
		for i in range(len(p)):
			anc = p[i]
			dist = (len(p)-1)-i
			all_dists.add((anc, child, dist))
	all_dists = sorted(all_dists)
	return all_dists

''' test

#      A
#     / \
#    B   C
#     \ / 
#      F

pdict = {"A":["B", "C"], "B":["F"], "C":["F"]}
all_paths=[]
get_all_paths(pdict, "A", [], all_paths)
get_all_dists(all_paths) == [('A', 'A', 0), ('A', 'B', 1), ('A', 'C', 1), ('A', 'F', 2), ('B', 'B', 0), ('B', 'F', 1), ('C', 'C', 0), ('C', 'F', 1), ('F', 'F', 0)]

'''



