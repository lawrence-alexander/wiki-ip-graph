import json
import requests
import requests_cache
import time
import maxminddb
import networkx as nx
import argparse

#==================================================================================#
#   Generates network graph of Wikipedia IP edits to locale and service provider   #
#           by Lawrence Alexander la2894@my.open.ac.uk @LawrenceA_UK               #
#==================================================================================#


#===============================================================================================#
# This product includes GeoLite2 data created by MaxMind, available from http://www.maxmind.com #
#===============================================================================================#

ap = argparse.ArgumentParser()
ap.add_argument ("-a","--wikiarticle",required=False,help="Exact title of Wikipedia article to query.")
ap.add_argument ("-f","--articlefile",required=False,help="File containing list of Wiki articles titles to query.")
ap.add_argument ("-o","--outfile",required=True,help="Name of graph output GEXF file")
arguments = vars(ap.parse_args())

# Set User-Agent header
headers = {'User-Agent':'Anonymous revisions research tool (la2894@my.open.ac.uk); Uses Python 2.7/Requests'}

# Base Wiki API endpoint
wiki_base_url = "https://en.wikipedia.org/w/api.php"

# Initialise http cache to reduce load on API
requests_cache.install_cache(cache_name='wiki_cache', backend='sqlite', expire_after=None)

# MaxMind database paths
country_db = ""
city_db = ""
asn_db=""

#
# Function to retrieve data for anonymous revisions
#
def get_revisions(article_title,rvcontinue,timestamp_ip):
        revisions_query_url = wiki_base_url + "?action=query&prop=revisions&titles=%s&rvprop=flags|timestamp|user|userid&rvlimit=500%s&maxlag=3&format=json" % (article_title,rvcontinue)
        response = requests.get(revisions_query_url, headers=headers)        
        if response.status_code == 200:                
                revisions_result = json.loads (response.content)                
                # Handle maxlag
                try:
                        if revisions_result['error']['code']=='maxlag':
                                print "[>] Hit maxlag limit (%s). Retrying in 5 seconds..." % revisions_result['error']['info']
                                time.sleep(5)
                                timestamp_ip = get_revisions(article_title,rvcontinue='')
                except:
                        pass
                
                for page_id in revisions_result['query']['pages']:
                        page_id = page_id
                        for rev in revisions_result['query']['pages'][page_id]['revisions']: 
                                # Add timestamp and IP details of anonymous edits                                
                                try: 
                                        rev['anon']
                                        ip_addresses.append(rev['user'])                                        
                                        timestamp_ip[rev['timestamp']]=rev['user']
                                        ip_timestamp[rev['user']]=rev['timestamp']
                                        
                                except:
                                        pass 
        # If there are further results available, recursively page through them
        try:
                if revisions_result['continue']['rvcontinue']:
                        rvcontinue= "&rvcontinue=%s" % revisions_result['continue']['rvcontinue']                        
                        timestamp_ip.update(get_revisions(article_title,rvcontinue,timestamp_ip=timestamp_ip))
                else:
                        print "[!] Error accessing API - returned code: %d" % response.status_code
                        return None
        except:
                pass
        return timestamp_ip
        
#
# Query MaxMind GeoLite2 database
#
def query_maxmind(mm_query,mm_database_path):
        reader=maxminddb.open_database(mm_database_path)
        mm_data=reader.get(mm_query)        
        return mm_data

#==================#
# End of functions #
#==================#

out_graph=arguments['outfile']

# List to hold edit IPs
ip_addresses=[]

# List of Wiki articles to get edit IPs from
article_titles =[]

# Pass in single article title, if set
if arguments['wikiarticle'] is not None:
        article_titles.append([arguments['wikiarticle']])
        
# Otherwise load from list of article titles     
else:   
        inputfile=arguments['articlefile']  
        with open(inputfile) as infile:    
                for wiki_title in infile:
                        wiki_title=wiki_title.strip()
                        article_titles.append(wiki_title)
                infile.close() 
                
# Iteratively retrieve anon edit IPs for each Wiki article
graph=nx.DiGraph()
for article_title in article_titles:
        if article_title is not '':
                print "Getting revisions for article: '%s'..." % article_title
                timestamp_ip = get_revisions(article_title,rvcontinue='',timestamp_ip={})
                print "[*] Found %d IP addresses..." % len(ip_addresses) 
                
                # Enrich with MaxMind databases             
                maxmind_options = {'country':True,'city':False,'ASN':True}
                print "Now querying MaxMind databases..."               
                graph.add_node(article_title,type='SourceWikiArticle')                
                for timestamp, mm_query in timestamp_ip.iteritems():
                        graph.add_node(mm_query,type='IPv4Address')
                        graph.add_edge(article_title,mm_query)
                        
                        # Add IP ---> country relationships
                        if maxmind_options['country']==True:
                                try:
                                        
                                        mm_data=query_maxmind(mm_query,mm_database_path=country_db)
                                        country_code= mm_data['country']['iso_code']
                                        country_name= mm_data['country']['names']['en']
                                        graph.add_node(country_code,type="CountryCode")
                                        graph.add_node(country_name,type="CountryName")
                                        graph.add_edge(mm_query,country_code)
                                        graph.add_edge(mm_query,country_name)   
                                        
                                except:
                                        pass
                        # Add IP ---> ASN
                        if maxmind_options['ASN']==True:
                                try:
                                        
                                        mm_data=query_maxmind(mm_query,mm_database_path=asn_db)
                                        as_org=mm_data['autonomous_system_organization']
                                        asn=mm_data['autonomous_system_number']
                                        graph.add_node(as_org,type="ASN-Organization")
                                        graph.add_node(asn,type="Autonomous System Number")
                                        graph.add_edge(mm_query,as_org)
                                        graph.add_edge(mm_query,asn) 
                                        
                                except:
                                        pass
                        
                        # Add Ip --> city
                        if maxmind_options['city']==True:
                                
                                try:
                                        mm_data=query_maxmind(mm_query,mm_database_path=city_db)
                                        city_name= mm_data['city']['names']['en']
                                        graph.add_node(city_name,type="City")
                                        graph.add_edge(mm_query,city_name)
                                        
                                except:
                                        pass
        
# Write out data to GEXF graph         
nx.write_gexf(graph,out_graph)
print "[*] Complete. Graph written as: %s." % out_graph







