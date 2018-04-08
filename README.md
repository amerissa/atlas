Apache Atlas Population Script with IBM IGC Integration
===================

Update script will populate Atlas with attributes. You can add custom attributes and populate them. Tags can be created and entities can be tagged on the fly.

IGC Integration will check if term is present in IGC and associate term as an attribute in Atlas and include the definition of the term as  an extra attribute 

For hive updates:
specify type as hive in JSON

For hdfs updates:
specify type as hdfs in JSON

For custom types:
specify type as the type in JSON
specify name as the fully qualified name in JSON

Hive Integration will iterate over tables and columns. One JSON input per database. 

----------


Config File
-------------

[atlas]

//Setup connection to Atlas

port=21000

host=localhost.localdomain

username=admin

password=admin

clustername=amer

hdfsnameservice=hdfs://localhost.localdomain:8020

[properties]

#setting it to true will create attributes and tags if they do not exist

createAttributeDynamically=True

jsonFile=file.json



[IGC]

#Enable Sync from IGC

IGCSync=True

#Attribute to read and check whether it exists in IGC. The definition will be added under eg

EnterpriseBusinessGlossaryTermDefinition

IGCAttribute=EnterpriseBusinessGlossaryTerm

#Parent Category to search Under

IGCRootGlossary=Enterprise Business Glossary

#IGC Connection Info

IGC=https://localhost.localdomain:9443/ibm/iis/igc-rest/v1/

IGCUser=guest

IGCPassword=Password1



----------


JSON Structure
-------------------
Sample JSON:
```json
{
"name" : "DATABASENAME",
"type" : "hive",
"attributes": [
  { "Zone" : "test1" },
  {"description" : "test1" } ],
"tags" : [ "testnew", "test2" ],
"tables" : [
  {
    "name" : "salaries",
    "attributes" : [
      {"BusinessFullDesc" : "test1"},
      {"BusinessShortDesc" : "test1"}],
    "tags" : ["testnew"],
    "columns" : [
      {
      "name" : "emp_no",
      "attributes" : [
        {"BusinessDescription" : "test1"},
        {"EnterpriseBusinessGlossaryTerm" : "Address"},,
      "tags" : ["testnew"]
    },
    {
    "name" : "salary",
    "attributes" : [
      {"BusinessDescription" : "test1"},
      {"EnterpriseBusinessGlossaryTerm" : "test"},
      {"comment" : "test"},
      {"description" : "test"}],
    "tags" : ["amer"]
    }
    ]
  },
  {
    "name" : "employees",
    "attributes" : [
      {"BusinessFullDesc" : "test1"},
      {"BusinessShortDesc" : "test"},
      {"ConfidentialityClassifcation" : "test"},
      {"CountryOfOrigin" : "test"},
      {"DataOwner" : "test"},
      {"FeedCode" : "test"},
      {"FeedName" : "test"},
      {"description" : "test"},
      {"Frequency" : "test"},
      {"comment" : "test"}],
    "tags" : ["testnew"],
    "columns" : [
      {
      "name" : "emp_no",
      "attributes" : [
        {"BusinessDescription" : "test"},
        {"EnterpriseBusinessGlossaryTerm" : "test"},
        {"comment" : "test"},
        {"description" : "test"}],
      "tags" : ["testnew"]
    },
    {
    "name" : "salary",
    "attributes" : [
      {"BusinessDescription" : "test1"},
      {"EnterpriseBusinessGlossaryTerm" : "test"},
      {"comment" : "test"},
      {"description" : "test"}],
    "tags" : ["amer"]
    }
 ] } ] }
```
