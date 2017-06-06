# atlas
Atlas Related scripts 

updater.py

Script will update and create attributes and tags in Atlas

CSV File Example

DATABASE,TABLE,COLUMN,ATTRIBUTE,VALUE

Leaving the column empty it will assume it will update table, leaving table and column empty it will assume it is a database.

Specifying tag as the ATTRIBUTE it will tag the entity with tag name of VALUE

Dynamic mode will create missing attributes and tags if they do not exist in ATlas


Examples:

./updater.py file.csv 
./updater.py file.csv dynamic


file.csv:
default,employees,,BusinessDescription,Employeess Tables for employee information
employees,salaries,,BusinessDescription,Employeess Tables for salaries information
employees,salaries,,DataProvider,HR Oracle Instance #134
employees,salaries,emp_no,OnBoarding,NPIF
employees,salaries,,tag,amer
employees,salaries,emp_no,EADescription,HR Information For Employees

