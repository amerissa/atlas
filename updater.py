#!/bin/python
import json
import requests
import sys
import csv
import getopt

### Atlas Environment variables
ATLAS_PORT="21000"
ATLAS_DOMAIN="localhost.localdomain"
USERNAME="admin"
PASSWORD="admin"
CLUSTERNAME="amer"

failedupdates = 0
successfulupdates = 0

try:
    csvfile=sys.argv[1]
except IndexError:
    print "Provide csv file location"
    sys.exit(1)

try:
    dynamic = sys.argv[2]
except IndexError:
    print "Will not create fields"
    dynamic = False

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
       if dynamic == "dynamic":
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
        if dynamic == "dynamic" :
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
                global failedupdates
                failedupdates += 1
                print "Failed to update property %s for %s" % (updateProperty, FQDN)
            else:
                print "Updated property %s for %s" % (updateProperty, FQDN)
                global successfulupdates
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

#READ CSV Dictionary
reader = csv.reader(open(csvfile))

#Process Entries
for row in reader:
    if not (row):
        continue
    else:
        database = row[0]
        table = row[1]
        column = row[2]
        updateProperty = row[3]
        newValue = row[4]
        path = [database, table, column]
        path = filter(None, path)
        FQDN = ".".join(path) + '@' + CLUSTERNAME
        entitytype = hivetype(database, table, column)
        if not checkentityexists(entitytype, FQDN):
            continue
        GUIid = getGID(entitytype, FQDN)
        if updateProperty == "tag":
            processtag(newValue, GUIid, FQDN)
        else:
            proceessattribute(entitytype, updateProperty, FQDN, GUIid, newValue)

if failedupdates == 0 and successfulupdates == 0:
    print "Nothing To Update"
else:
    print "Finished Updating. Successful: %s. Failed: %s." % (successfulupdates, failedupdates)
