# Planet Food
Online restaurant menus.  

### Requirements
- [Python 2.7](https://www.python.org/downloads/)
- [SQLAlchemy](http://www.sqlalchemy.org/download.html)
- [Virtual Box](https://www.virtualbox.org/wiki/Downloads)
- [Vagrant](https://www.vagrantup.com/downloads.html)


### Folders/Files
- `static` contains css and image files.
- `templates` contains html files.
- `project.py` creates web server and handles URL routing.
- `helpers.py` contains helper functions to get user info.
- `database_setup.py` defines the database schema.
- `lotsofmenus.py` populates the database for development/debugging purposes.
- `client_secrets.json` contains information such as the client ID for google authentication. 

### Usage
- Clone [this repository](https://github.com/kingdivine/planet-food.git)
- On your terminal, navigate to the tournament folder containing the project files and type `vagrant up` to turn on the virtual machine followed by `vagrant ssh` to log in.  
- Create the database by running the command `python database_setup.py`.
- Populate the database by running the command `python lotsofmenus.py`.
- Launch the server by running the command `python project.py`. 
- Navigate to http://localhost:5000/login to start using the site. 
- Make changes to any of the files to add more functionality/ extra features to the site. 


### License
MIT License
