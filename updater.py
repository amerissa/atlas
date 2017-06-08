#!/usr/bin/python
import json
import requests
import sys
from ConfigParser import SafeConfigParser
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


def atlasREST( restAPI ) :
    url = "http://"+ATLAS_DOMAIN+":"+ATLAS_PORT+restAPI
    r= requests.get(url, auth=(USERNAME, PASSWORD))
    return(json.loads(r.text))

def atlasPOST( method, restAPI, data) :
    url = "http://" + ATLAS_DOMAIN + ":" + ATLAS_PORT + restAPI
    r = requests.request(method ,url, auth=(USERNAME, PASSWORD), headers={"Content-Type": "application/json"}, data=data)
    return (json.loads(r.text));

def atlascheck():
    url = "http://" + ATLAS_DOMAIN + ":" + ATLAS_PORT + "/api/atlas/admin/status"
    status = requests.get(url, auth=(USERNAME, PASSWORD))
    if status.status_code == 200:
        if json.loads(status.text)["Status"] == "ACTIVE":
            try:
                atlasREST("/api/atlas/types")
            except:
                print "Cannot connect to Atlas: possibly username and password are wrong"
                sys.exit(1)
            return True
        else:
            print "Atlas Health is " + status["Status"]
            return False
    else:
        sys.exit(1)
        return False

def checkentityexists(entitytype, FQDN) :
    entity=atlasREST("/api/atlas/entities?type=%s&property=qualifiedName&value=%s" % (entitytype, FQDN))
    for key, value in entity.items():
        if key == "error":
            print "Cannot update " + FQDN + " Reason: " + value
            global failedupdates
            failedupdates += 1
            return False
        else:
            return True

def getGID(entitytype, FQDN) :
    entity=atlasREST("/api/atlas/entities?type=%s&property=qualifiedName&value=%s" % (entitytype, FQDN))
    GUIid=entity['definition']['id']['id']
    return(GUIid)

def getProperties(GUIid) :
    properties=atlasREST("/api/atlas/entities/%s" %  (GUIid))
    return(properties)


def checkattribute(entitytype, attribute) :
    list = atlasREST("/api/atlas/types/%s?type=entity" % (entitytype))["definition"]["classTypes"][0]
    attributes = [ item["name"] for item in list["attributeDefinitions"] ]
    if attribute in attributes or attribute == "description":
        return True
    else:
       if dynamic == True:
           createattribute(entitytype, attribute)
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
        if updateProperty == IGCAttribute:
            if IGCSync == True:
                if not processIGC(newValue, entitytype, FQDN, GUIid):
                    return False
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

def processIGC(newValue, entitytype, FQDN, GUID):
    global failedupdates
    global successfulupdates
    if not IGCCheck(newValue):
        failedupdates += 1
        print "Failed to update property %s for %s. Reason: It does not Exist in IGC" % (IGCAttribute, FQDN)
        return False
    else:
        if not checkattribute(entitytype, IGCAttribute + "Definition"):
            createattribute(entitytype, IGCAttribute + "Definition")
        arguments = {'types' : 'term', 'text' : '"' +  newValue + '"', 'search-properties' : 'name'}
        IGCid = IGCRest("search", arguments)['items'][0]['_id']
        shortdescription = IGCRest("assets/" + IGCid)["short_description"]
        proceessattribute(entitytype, IGCAttribute + "Definition", FQDN, GUID, shortdescription)
        return True

def createattribute(entitytype, attribute) :
    instance = { "name" : attribute, "dataTypeName": "string", "multiplicity": "optional", "isComposite": False, "isUnique": False, "isIndexable": True, "reverseAttributeName": None}
    definition = atlasREST("/api/atlas/types/%s" % (entitytype))
    del definition["requestId"]
    del definition["typeName"]
    definition["definition"]["classTypes"][0]["attributeDefinitions"].append(instance)
    definition = definition.pop("definition")
    post = atlasPOST( "PUT" ,"/api/atlas/types", json.dumps(definition))

def IGCRest(path, arguments=''):
    results = json.loads(requests.get(IGC + path, auth=(IGCUser, IGCPassword), verify=False, params=arguments).text)
    return(results)

def IGCCheck(newValue):
    arguments = {'types' : 'term', 'text' : '"' +  newValue + '"', 'search-properties' : 'name'}
    results = IGCRest("search", arguments)["items"]
    for result in results:
        for category in result["_context"]:
            if IGCRootGlossary == category['_name']:
                return True
            else:
                return False

def updater(data, entitytype, FQDN):
    if not checkentityexists(entitytype, FQDN):
        return False
    else:
        GUIid = getGID(entitytype, FQDN)
        for property in data["attributes"]:
            for updateProperty, newValue in property.items():
                proceessattribute(entitytype, updateProperty, FQDN, GUIid, newValue)
        for tag in data["tags"]:
            processtag(tag, GUIid, FQDN)
        return True

def hive(jsondata):
    FQDN = jsondata["name"] + "@" + CLUSTERNAME
    if updater(jsondata, "hive_db", FQDN):
        for table in jsondata["tables"]:
            tableFQDN = jsondata["name"] + '.' + table["name"] + "@" + CLUSTERNAME
            if updater(table, "hive_table",  tableFQDN):
                for column in table['columns']:
                    columnFQDN = jsondata["name"] + '.' + table["name"] + '.' + column["name"] +  "@" + CLUSTERNAME
                    updater(column, "hive_column", columnFQDN)

def hdfs(jsondata):
    FQDN = hdfsnameservice + jsondata["name"]
    updater(jsondata, "hdfs_path", FQDN)

def results():
    if failedupdates == 0 and successfulupdates == 0:
        print "Nothing To Update"
    else:
        print "Finished Updating. Successful: %s. Failed: %s." % (successfulupdates, failedupdates)

####################################################

failedupdates = 0
successfulupdates = 0

#Read Config File

try:
    configfile=sys.argv[1]
except IndexError:
    print "Provide config file location"
    sys.exit(1)

settings = SafeConfigParser()

settings.read(configfile)

### Atlas Environment variables
ATLAS_PORT=settings.get('atlas', 'port')
ATLAS_DOMAIN=settings.get('atlas', 'host')
USERNAME=settings.get('atlas', 'username')
PASSWORD=settings.get('atlas', 'password')
CLUSTERNAME=settings.get('atlas', 'clustername')
hdfsnameservice=settings.get('atlas', 'hdfsnameservice')

dynamic=settings.getboolean('properties','createAttributeDynamically')
jsonfile=settings.get('properties', 'jsonFile')

#IGC
IGC=settings.get('IGC', 'IGC')
IGCUser=settings.get('IGC', 'IGCUser')
IGCPassword=settings.get('IGC', 'IGCPassword')
IGCSync=settings.getboolean('IGC','IGCSync')
IGCAttribute=settings.get('IGC', 'IGCAttribute')
IGCRootGlossary=settings.get('IGC', 'IGCRootGlossary')

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

#Run Logic
if jsondata["type"] == "hive":
    hive(jsondata)
elif jsondata["type"] == "hdfs":
    hdfs(jsondata)
else:
    print "Type %s is not supported" % (jsondata["type"])
    sys.exist(1)

results()
