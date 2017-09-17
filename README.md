This script will take in Wikipedia article names and produce a GEXF entity-relationship graph from IP addresses of anonymous edits to location and service provider details based on MaxMind's GeoLite databases.

Applications include researching Wiki page vandalism (though note that by no means all IP edits are malicious) and general demographics of anonymous contributors.

Usage: 

wiki_ip_graph.py -a [wikipedia page title] -f [text file containing list of pages to query] -o [output graph filename]

