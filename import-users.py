#! /usr/bin/env python
# import-users.py

"""
Import repository users from a JSON file. Users who do not exist will be 
created and existing users will be updated.

Usage: python import-users.py file.json [options]

Options and arguments:

file.json           Name of the JSON file to import user information from. 

-u user             The username to authenticate as
--username=user

-p pass             The password to authenticate with
--password=pass

-U url              The URL of the Share web application, e.g. 
--url=url           http://alfresco.test.com/share

--users=arg         Comma-separated list of user names to import. Users in the
                    JSON file whose user names do not exactly match one of the 
                    values will be skipped and not created.

--skip-users=arg    Comma-separated list of user names to exclude from the 
                    import

--no-dashboards     Do not set user dashboard configurations

--no-preferences    Do not set user preferences

--no-update-profile Do not update profile information after creation. The 
                    default behaviour is to send a request to the edit user 
                    profile form handler to update values for existing users 
                    and for new users to set any properties that the create 
                    operation does not set itself.

--no-avatars        Do not upload user profile images

--create-only       Create missing users and do nothing else. Equivalent to 
                    --no-dashboards --no-preferences --no-preferences 
                    --no-update-profile --no-avatars

-d                  Turn on debug mode

-h                  Display this message
--help
"""

import getopt
import json
import os
import sys

import alfresco

# HTTP debugging flag
global _debug

def usage():
    print __doc__

def main(argv):

    username = "admin"
    password = "admin"
    url = "http://localhost:8080/share"
    include_users = None
    skip_users = [ 'System' ]
    set_dashboards = True
    set_prefs = True
    update_profile = True
    set_avatars = True
    _debug = 0
    
    if len(argv) > 0:
        if argv[0] == "--help" or argv[0] == "-h":
            usage()
            sys.exit()
        elif argv[0].startswith('-'):
            usage()
            sys.exit(1)
        else:
            # File name to load users from
            # TODO Support stdin as input mechanism
            filename = argv[0]
    else:
        usage()
        sys.exit(1)
    
    try:
        opts, args = getopt.getopt(argv[1:], "hdu:p:U:", ["help", "username=", "password=", "url=", "users=", "skip-users=", "no-dashboards", "no-preferences", "no-update-profile", "no-avatars", "create-only"])
    except getopt.GetoptError, e:
        usage()
        sys.exit(1)
    
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit()
        elif opt == '-d':
            _debug = 1
        elif opt in ("-u", "--username"):
            username = arg
        elif opt in ("-p", "--password"):
            password = arg
        elif opt in ("-U", "--url"):
            url = arg
        elif opt == "--users":
            include_users = arg.split(',')
        elif opt == "--skip-users":
            skip_users = arg.split(',')
        elif opt == '--no-dashboards':
            set_dashboards = False
        elif opt == '--no-preferences':
            set_prefs = False
        elif opt == '--no-update-profile':
            update_profile = False
        elif opt == '--no-avatars':
            set_avatars = False
        elif opt == '--create-only':
            set_dashboards = False
            set_prefs = False
            update_profile = False
            set_avatars = False
    
    sc = alfresco.ShareClient(url, debug=_debug)
    print "Log in (%s)" % (username)
    loginres = sc.doLogin(username, password)
    if not loginres['success']:
        print "Could not log in using specified credentials"
        sys.exit(1)
    users = json.loads(open(filename).read())['people']
    create_users = []
    
    # Filter the users
    for u in users:
        if (include_users is None or str(u['userName']) in include_users) and u['userName'] not in skip_users:
            create_users.append(u)
    
    for u in create_users:
        # Work around bug where create/update user calls do not accept null values
        # Create call does not like jobtitle being null; webtier update profile does not tolerate any being null
        for k in u.keys():
            if u[k] is None:
                u[k] = ""
        # Set password to be the same as the username if not specified
        if 'password' not in u:
            u['password'] = u['userName']
            
    try:
        print "Create %s user(s)" % (len(create_users))
        sc.createUsers(create_users, skip_users=skip_users)
        
        # Set user preferences
        for u in create_users:
            if 'preferences' in u and len(u['preferences']) > 0 and set_prefs:
                print "Setting preferences for user '%s'" % (u['userName'])
                sc.setUserPreferences(u['userName'], u['preferences'])
    finally:
        print "Log out (%s)" % (username)
        sc.doLogout()
    
    #TODO Check if a profile image or dashboard config is available before logging in
    thisdir = os.path.dirname(filename)
    for u in create_users:
        if set_avatars or update_profile or set_dashboards:
            print "Log in (%s)" % (u['userName'])
            sc.doLogin(u['userName'], u['password'])
            try:
                # Add profile image
                if set_avatars:
                    print "Setting profile image for user '%s'" % (u['userName'])
                    if 'avatar' in u:
                        try:
                            sc.setProfileImage(u['userName'], thisdir + os.sep + str(u['avatar']))
                        except IOError, e:
                            if e.errno == 2:
                                # Ignore file not found errors
                                pass
                            else:
                                raise e
                # Update user profile
                if update_profile:
                    print "Updating profile information for user '%s'" % (u['userName'])
                    sc.updateUserDetails(u)
                # Update dashboard
                if 'dashboardConfig' in u and set_dashboards:
                    print "Updating dashboard configuration for user '%s'" % (u['userName'])
                    sc.updateUserDashboardConfig(u)
            finally:
                print "Log out (%s)" % (u['userName'])
                sc.doLogout()

if __name__ == "__main__":
    main(sys.argv[1:])
