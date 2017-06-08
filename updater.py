#!/usr/bin/python
import json
import requests
import sys
from ConfigParser import SafeConfigParser
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

failedupdates = 0
successfulupdates = 0
settings = SafeConfigParser()

try:
    configfile=sys.argv[1]
except IndexError:
    print "Provide config file location"
    sys.exit(1)

settings.read(configfile)

### Atlas Environment variables
ATLAS_PORT=settings.get('atlas', 'port')
ATLAS_DOMAIN=settings.get('atlas', 'host')
USERNAME=settings.get('atlas', 'username')
PASSWORD=settings.get('atlas', 'password')
CLUSTERNAME=settings.get('atlas', 'clustername')

dynamic=settings.getboolean('properties','createAttributeDynamically')
jsonfile=settings.get('properties', 'jsonFile')



def atlasREST( restAPI ) :
    url = "http://"+ATLAS_DOMAIN+":"+ATLAS_PORT+restAPI
    r= requests.get(url, auth=(USERNAME, PASSWORD))
    return(json.loads(r.text))

def atlasPOST( method, restAPI, data) :
    url = "http://" + ATLAS_DOMAIN + ":" + ATLAS_PORT + restAPI
    r = requests.request(method ,url, auth=(USERNAME, PASSWORD), headers={"Content-Type": "application/json"}, data=data)
    return (json.loads(r.text));

def atlascheck():
    try:
        atlasREST("/api/atlas/types")
    except:
        print "Cannot connect to Atlas: possibly username and password are wrong"
        sys.exit(1)
    url = "http://" + ATLAS_DOMAIN + ":" + ATLAS_PORT + "/api/atlas/admin/status"
    status = requests.get(url, auth=(USERNAME, PASSWORD))
    if status.status_code == 200:
        if json.loads(status.text)["Status"] == "ACTIVE":
            return True
        else:
            print "Atlas Health is " + status["Status"]
            return False
    else:
        return False

def checkentityexists(hivetype, FQDN) :
    entity=atlasREST("/api/atlas/entities?type=%s&property=qualifiedName&value=%s" % (hivetype, FQDN))
    for key, value in entity.items():
        if key == "error":
            print "Cannot update " + FQDN + " Reason: " + value
            global failedupdates
            failedupdates += 1
            return False
        else:
            return True

def getGID(hivetype, FQDN) :
    entity=atlasREST("/api/atlas/entities?type=%s&property=qualifiedName&value=%s" % (hivetype, FQDN))
    GUIid=entity['definition']['id']['id']
    return(GUIid)

def getProperties(GUIid) :
    properties=atlasREST("/api/atlas/entities/%s" %  (GUIid))
    return(properties)

def hivetype(database, table, column) :
     if column and table and database:
        type = 'hive_column'
     elif table and database:
        type = 'hive_table'
     else:
        type = 'hive_db'
     return(type)

def checkattribute(hivetype, attribute) :
    list = atlasREST("/api/atlas/types/%s?type=entity" % (hivetype))["definition"]["classTypes"][0]
    attributes = [ item["name"] for item in list["attributeDefinitions"] ]
    if attribute in attributes or attribute == "description":
        return True
    else:
       if dynamic == True:
           createattribute(hivetype, attribute)
           return True
       else:
           return False

def processtag(tagname, gid, fqdn):
    if tagname in atlasREST("/api/atlas/types?type=trait")["results"]:
        if tagname not in atlasREST("/api/atlas/entities/%s" %  (gid))["definition"]["traits"]:
            data = {  "jsonClass":"org.apache.atlas.typesystem.json.InstanceSerialization$_Struct", "typeName": tagname, "values":{} }
            post = atlasPOST( "POST" ,"/api/atlas/entities/%s/traits" % (gid), json.dumps(data) )
            print "Added Tag %s to %s" % (tagname, fqdn)
            global successfulupdates
            successfulupdates += 1
            return True
        else:
            return True
    else:
        if dynamic == True :
            data = { "enumTypes": [], "structTypes": [], "traitTypes": [ { "superTypes":[], "hierarchicalMetaTypeName":"org.apache.atlas.typesystem.types.TraitType", "typeName": tagname, "typeDescription": None, "attributeDefinitions":[] }], "classTypes": [] }
            post = atlasPOST( "POST" ,"/api/atlas/types", json.dumps(data) )
            print "Created Tag: " + tagname
            processtag(tagname, gid, fqdn)
            return True
        else:
            print "Cannot update %s Reason: Tag %s does not exist" % (fqdn, tagname)
            global failedupdates
            failedupdates += 1
            return False


def proceessattribute(entitytype, updateProperty, FQDN, GUIid, newValue):
    global successfulupdates
    global failedupdates
    if not checkattribute(entitytype, updateProperty):
       print "Attribute %s for %s does not exist in Atlas" % (updateProperty, FQDN)
    else:
        properties = getProperties(GUIid)
        if newValue.isdigit():
            newValue = int(newValue)
            currentprop = int(properties['definition']['values'][updateProperty])
        else:
            currentprop = properties['definition']['values'][updateProperty]
        if newValue != currentprop :
            updateTable = atlasPOST( "POST", "/api/atlas/entities/%s?property=%s" % (GUIid,updateProperty), str(newValue))
            if "error" in updateTable:
                print "Failed to update property %s for %s" % (updateProperty, FQDN)
                failedupdates += 1
            else:
                print "Updated property %s for %s" % (updateProperty, FQDN)
                successfulupdates += 1


def createattribute(hivetype, attribute) :
    instance = { "name" : attribute, "dataTypeName": "string", "multiplicity": "optional", "isComposite": False, "isUnique": False, "isIndexable": True, "reverseAttributeName": None}
    definition = atlasREST("/api/atlas/types/%s" % (hivetype))
    del definition["requestId"]
    del definition["typeName"]
    definition["definition"]["classTypes"][0]["attributeDefinitions"].append(instance)
    definition = definition.pop("definition")
    post = atlasPOST( "PUT" ,"/api/atlas/types", json.dumps(definition))


#CHECK IF ATLAS IS UP
try:
    atlascheck()
except:
    print "Cannot connect to Atlas"
    sys.exit(1)

#READ JSON Dictionary
try:
    jsondata=json.loads(open(jsonfile).read())
except:
    print "File does not exist or not accesiable"
    sys.exit(1)


db = jsondata["dbname"]
dbFQDN = "%s@%s" % (db, CLUSTERNAME)

if not checkentityexists("hive_db", dbFQDN):
    print "Database %s does not exit. Not continuing" % (dbFQDN)
    sys.exit(1)

dbGUIid = getGID("hive_db", dbFQDN)

for property in jsondata["attributes"]:
    for updateProperty, newValue in property.items():
        proceessattribute("hive_db", updateProperty, dbFQDN, dbGUIid, newValue)
for tag in jsondata["tags"]:
    processtag(tag, dbGUIid, dbFQDN)

for table in jsondata["tables"]:
    tablename = table["name"]
    tableFQDN = "%s.%s@%s" % (db, tablename, CLUSTERNAME)
    if not checkentityexists("hive_table", tableFQDN):
        print "Table %s does not exit. Moving to next table" % (tableFQDN)
        continue
    else:
        tableGUIid = getGID("hive_table", tableFQDN)
        for property in table["attributes"]:
            for updateProperty, newValue in property.items():
                proceessattribute("hive_table", updateProperty, tableFQDN, tableGUIid, newValue)
        for tag in table["tags"]:
            processtag(tag, tableGUIid, tableFQDN)
        for column in table['columns']:
            columnname = column["name"]
            columnFQDN = "%s.%s.%s@%s" % (db, tablename, columnname, CLUSTERNAME)
            if not checkentityexists("hive_column", columnFQDN):
                print "Column %s does not exit. Moving to next column" % (columnFQDN)
                continue
            else:
                columnGUIid = getGID("hive_column", columnFQDN)
                for property in column["attributes"]:
                    for updateProperty, newValue in property.iteritems():
                        proceessattribute("hive_column", updateProperty, columnFQDN, columnGUIid, newValue)
                for tag in column["tags"]:
                    processtag(tag, columnGUIid, columnFQDN)

if failedupdates == 0 and successfulupdates == 0:
    print "Nothing To Update"
else:
    print "Finished Updating. Successful: %s. Failed: %s." % (successfulupdates, failedupdates)
