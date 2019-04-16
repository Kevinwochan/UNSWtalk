#!/web/cs2041/bin/python3.6.3

# https://cgi.cse.unsw.edu.au/~cs2041/assignments/UNSWtalk/

import os, collections, re,sys, dateutil.parser, datetime, shutil,smtplib,itsdangerous, subprocess
from flask import Flask, render_template, session, send_from_directory, send_file,request, redirect, url_for
from shutil import copy,copyfile
from itsdangerous import URLSafeSerializer, BadSignature
from email.mime.text import MIMEText



# global variables
students_dir = "dataset-medium";
unverified_accounts = {}

app = Flask(__name__)

# challenge for username and password
# posts = [post1,psot2,post3]
@app.route('/', methods=['GET','POST'])
def news_feed ():
	# if the user isnt logged in, send them to login page
	if not (session.get('logged_in',0)) or not verify_zid(session.get('zid',0)):
		return redirect ( url_for ( 'login' ) )
	
	student_zid = session.get('zid',0)
	posts = read_student_posts(student_zid)
	# add friend's posts
	for friend in read_student_profile(student_zid)['friends'] :
		posts.extend( read_student_posts( friend ) )

	# sort posts by most recent
	sorted_posts = sorted(posts, key=lambda post: post['time'],reverse=True) 
	return render_template('news_feed.html',student_zid=student_zid,student_posts=sorted_posts)

# log in page
@app.route('/login', methods=['GET','POST'])
def login ():
	
	# if user is already logged in 
	if session.get('logged_in',0) and session.get('zid',0):
		# redirect them to their profile page
		return redirect ( url_for ('profile_page',student_zid=session.get('zid',0)) )

	# store login profile from the html form
	student_zid = request.form.get('zid', '')
	password = request.form.get('password', '')
	# remove unwanted characters 
	student_zid = re.sub('\W', '', student_zid)

	# check html form for entries	
	if student_zid == '' or password == '':
		 return render_template('login.html')

	# check the username
	if not verify_zid ( student_zid ):
		return render_template('login.html', error="unknown zid")
	
	# check the password
	if not verify_password ( student_zid, password ):
		return render_template('login.html', error="wrong password")

	# store zid in session cookie
	session['zid'] = student_zid
	session['logged_in'] = 1
	
	return redirect ( url_for ('news_feed' ) )

# logs users out of their account by deleteing their session data
@app.route('/logout', methods=['POST','GET'])
def logout():
	session.pop('zid',0)
	session.pop('logged_in',0)
	return redirect(url_for ('login') )

# page allows user to recover password
@app.route('/passwordrecovery',methods=['POST','GET'])
def forgot_password_page ():
		
	# if user is already logged in 
	if session.get('logged_in',0) and session.get('zid',0):
		# redirect them to their profile page
		return redirect ( url_for ('profile_page',student_zid=session.get('zid',0)) )

	# store login profile from the html form
	student_zid = request.form.get('zid', '')
	# remove unwanted characters 
	student_zid = re.sub('\W', '', student_zid)

	# check html form for entries	
	if student_zid == '':
		 return render_template('recovery.html')

	# check the username
	if not verify_zid ( student_zid ):
		return render_template('login.html', error="unknown zid")

	# send verification link
	
	return render_template ('recovery.html',error="please check your email for the recovery link")

# page allows someone to register
@app.route('/register',methods=['POST','GET'])
def register ():
	
	student_zid = request.form.get('zid', '')

	if student_zid == '':
		return	render_template ('register.html')	

	if verify_zid (student_zid):
		render_template ('register.html',error="this zid has already been registered")

	if request.form.get('password','0') != request.form.get('confirm-password','1'):
		render_template ('register.html',error="your passwords did not match")

	# store login profile from the html form
	full_name = request.form.get('full_name','')
	password = request.form.get('password', '')
	email = request.form.get('email','')
	birthday = request.form.get('birthday','')
	home_suburb = request.form.get('home_suburb','')	
	program = request.form.get('program','')
	courses = request.form.get('courses','')
	

	# store unverified account details in global dict of unverified accounts
	unverified_accounts[student_zid] = create_unverified_acccount ( student_zid,password,full_name,email,birthday,home_suburb,program,courses )

	verification_link = get_activation_link( student_zid )

	message = "Hi"+full_name+",\nPlease click the link below to verify your UNSWtalk account\n"+verification_link+"\nTalk...to you soon!"

	# send link to email containing verification link
	send_email ( email,'UNSWTalk Email Verification', message )

	return render_template('registered.html')


# creates a student profile dictionary
def create_unverified_acccount ( student_zid,password,full_name,email,birthday,home_suburb,program,courses ):
	# create key value pairs
	unverified_account = {}
	unverified_account ['full_name'] = full_name
	unverified_account ['password'] = password
	unverified_account ['email'] = email
	unverified_account ['birthday'] = birthday
	unverified_account ['home_suburb'] = home_suburb
	unverified_account ['program'] = program
	unverified_account ['courses'] = courses

	return unverified_account


# actually writes folder and student.txt file to folder
def create_acccount ( zid,password,full_name,email,birthday,home_suburb,program,courses ):
	
	# finds the post directory 
	try :
		os.mkdir ( os.path.join(students_dir,zid) )
	except:
		print ("FOLDER"+os.path.join(students_dir,zid)+"ALREADY EXISTS, CONTINUING ACCOUNT CREATION")

	# prepare file string
	file_string = ""
	file_string = file_string + "zid: " + zid + "\n"
	file_string = file_string + "password: " + password + "\n"
	file_string = file_string + "full_name: " + full_name + "\n"
	file_string = file_string + "email: " + email + "\n"
	file_string = file_string + "birthday: " + birthday + "\n"
	file_string = file_string + "home_suburb: " + home_suburb + "\n"
	file_string = file_string + "program: " + program + "\n"
	file_string = file_string + "courses: (" + courses + ")\n"
	file_string = file_string + "friends: ( )" + "\n"
	file_string = file_string + "about_me: What are you interested in? edit your profile and let others know!" + "\n"
	print ("NEW USER CREATED")
	print (file_string)

	# write string to file
	with open( os.path.join(students_dir,zid,"student.txt"),"w" ) as f:
		f.write(file_string)
		
	return

# # # # code Piazza COMP2041 class forum, written by Andrew Taylor
def send_email(to, subject, message):

	mutt = [
			'mutt',
			'-s',
			subject,
			'-e', 'set copy=no',
			'-e', 'set realname=UNSWtalk',
			'--', to
	]

	subprocess.run(
			mutt,
			input = message.encode('utf8'),
			stderr = subprocess.PIPE,
			stdout = subprocess.PIPE,
	)

# # # #


# # # # # code from flask snippets
# http://flask.pocoo.org/snippets/50/

def get_serializer(secret_key=None):
	if secret_key is None:
		secret_key = app.secret_key
	return URLSafeSerializer(secret_key)


# app route to authenticate verification link
@app.route('/account-activation/<payload>')
def activate_user(payload):
	s = get_serializer()

	try:
		student_id = s.loads(payload)
	except BadSignature:
		flash('Invalid Verification Link')
		return redirect(url_for('/'))

	create_account (student_id,unverified_accounts[student_id]['password'],unverified_accounts[student_id]['email'],unverified_accounts[student_id]['birthday'],unverified_accounts[student_id]['home_suburb'],unverified_accounts[student_id]['program'],unverified_accounts[student_id]['courses'])

	unverified_accounts.pop(student_id,None)

	flash('Email verified! you may now log in with your zid and password')
	return redirect(url_for('/'))


# verification link generator
def get_activation_link(user):
	s = get_serializer()
	payload = s.dumps(user)
	return url_for('activate_user', payload=payload, _external=True)


# app route to authenticate password recovery link
@app.route('/password-recovery/<payload>')
def redeem_voucher(payload):
	s = get_serializer()

	try:
		user_id, voucher_id = s.loads(payload)
	except BadSignature:
		flash('Invalid Recovery Link')
		return redirect(url_for('/'))

	
	voucher.redeem_for(user)
	flash('Password Reset')

	return redirect(url_for('/'))



def get_redeem_link(user, voucher):
	s = get_serializer()
	payload = s.dumps([user, voucher])
	return url_for('reset_password', payload=payload, _external=True)

# # # # 


# serves a student's display picture
@app.route('/<string:student_zid>/display_picture', methods=['GET','POST'])
def serve_display_picture ( student_zid ):
	display_picture = os.path.join(students_dir, student_zid, "img.jpg")	

	# checks if student has profile picture
	if os.path.isfile ( display_picture ):	
		return send_file ( display_picture, as_attachment=True )
	# defaults onto a image under 'static' if student has no display picture
	else:
		return send_file ( 'static/user.jpg', as_attachment=True )

# URL to edit an already published post
@app.route('/<string:post_author>/posts/<string:post_id>/edit', methods=['GET','POST'])
def edit_comment_page ( post_author, post_id ):

	# if the user isnt logged in, send them to login page
	if not (session.get('logged_in',0)) or not verify_zid(session.get('zid',0)):
		return redirect ( url_for ( 'login' ) )
	
	post = read_post ( post_author, post_id+".txt" )

	# if the the user wasnt the post_author, redirect user back to post 
	# precaution against users trying to edit with GET 
	if post['from'] != session.get('zid'):
		return redirect ( url_for ( 'comment_on_post',post_author=post_author,post_id=post_id ) )

	# if the edit comment form is filled out
	if request.form.get('new-comment','') != '' and request.form.get('action') == 'Save':
		new_comment = request.form.get('new-comment')
		print ("EDIT COMMENT FUNCTION ")
		edit_comment ( new_comment,post_author, post_id )
		# once comment has been edited, send them back to the post
		return redirect ( url_for ( 'comment_on_post',post_author=post_author,post_id=post_id ) )

	return render_template ('edit-post.html',post=post, root_author=post_author)


# displays a speciific post and all it's comments
@app.route('/<string:post_author>/posts/<string:post_id>', methods=['GET','POST'])
def comment_on_post ( post_author, post_id ):

	# if the user isnt logged in, send them to login page
	if not (session.get('logged_in',0)) or not verify_zid(session.get('zid',0)):
		return redirect ( url_for ( 'login' ) )

	# if a comment was made
	if request.form.get('comment','0') != '0' and request.form.get('comment','0') != '':
		comment = request.form.get('comment','0')
		comment_author = session.get('zid')
		post = write_comment ( comment, comment_author, post_author, post_id )
		return render_template ('post.html',post=post, root_author=post_author)

	# if new post was made
	if post_id == '?':
		new_post_text = request.form.get('new_post','0')
		# write the new_post
		new_post = write_post ( session.get('zid'),new_post_text )
		# render the page to the new post
		return redirect ( url_for ('comment_on_post', post_author=new_post['from'],post_id=new_post['post_id'] ) )
		
	# if user wants to delete or edit post
	if request.form.get('action','0'):
		action = request.form.get('action',0) 
		print (action)
		if action == "Delete Comment":
			delete_comment (post_author,post_id)
			# redirect to parent page or profile page
			if re.match ( "\d+-[-\d]+\.txt",post_id ) :
				parent_post = re.sub( "-\d+\.txt",".txt",post_id )
				return render_template ('post.html',post=parent_post, root_author=post_author)
			else:
				return redirect ( url_for ( 'profile_page',student_zid=session.get('zid') ))

		elif action == "Edit Comment":
			return redirect ( url_for ( 'edit_comment_page',post_author=post_author,post_id=post_id ))

	# save the filename of parent post
	post_filename = post_id+".txt"
	post = read_post ( post_author, post_filename )

	# display post and all it's comments, root_author is for the URL
	return render_template ('post.html',post=post, root_author=post_author)


# creates a new post
def write_post ( student_zid,post_text ):

	# create a path to where we're going to save the file 
	post_directory = os.path.join ( students_dir,student_zid )

	# prepare strings to write to file 
	time = "time: " + datetime.datetime.now().isoformat(timespec='seconds') + "+0000"
	message = "message: " + post_text
	author = "from: " + student_zid

	file_string = "\n".join( [time,message,author] )
	print (file_string)
	# find an unused filename to store post
	post_id = 0
	while str(post_id)+".txt" in sorted(os.listdir(post_directory)):
		post_id += 1

	post_file = str(post_id) + ".txt"
	post_path = os.path.join ( post_directory,post_file )
	with open ( post_path,"w" ) as f:
		f.write ( file_string ) 
	print ("NEW POST CREATED IN " + post_path)
	return read_post ( student_zid,post_file )


# returns a dict of the new comment
# writes a comment as a child of post_id
def write_comment ( comment , comment_author, post_author, post_id ):
	# finds the post directory 
	post_directory = os.path.join ( students_dir, post_author )
	# prepare file string
	time = "time: " + datetime.datetime.now().isoformat(timespec='seconds') + "+0000"
	message = "message: " + comment
	author = "from: " + comment_author
	file_string = "\n".join( [time,message,author] )

	# increment filename until the file does not exist
	comment_id = 0
	while post_id+"-" + str(comment_id)+".txt" in sorted(os.listdir(post_directory)):
		comment_id += 1
	new_comment_filename = post_id + "-" + str(comment_id) + ".txt"

	# write string to file
	with open( os.path.join(post_directory,new_comment_filename),"w" ) as f:
		f.write(file_string)
	# returns a dict of the new post
	return


# deletes old comment and writes new one
def edit_comment ( new_comment,post_author, post_id ):
	# finds the post directory 
	post_file = os.path.join ( students_dir, post_author,post_id+".txt" )
	temp_file = os.path.join ( students_dir, post_author,post_id+".tmp" )
	# backup old comment file 
	copy ( post_file,temp_file )
	# prepare new file string
	new_comment_string = ""
	with open ( temp_file ) as f:
		for line in f:
			if re.search ( "^message:",line ):
				new_line ="message: " + new_comment + " (edited)\n"
			else:
				new_line = line
			new_comment_string = new_comment_string + new_line
 
	os.remove(temp_file)
	# write string to file
	with open ( post_file,"w" ) as f:
		f.write ( new_comment_string )

	print("POST EDITED NEW POST READS "+ new_comment_string)
	print(post_file+"OVERWRITTEN")
	return


# delete comment and all of his children
# the post authour and comment author have edit rights
def delete_comment ( post_author, post_id ):
	# finds the post directory 
	post_directory = os.path.join ( students_dir, post_author )
	for comment in os.listdir ( post_directory ):

		comment_file = os.path.join( post_directory,comment )
		# delete all child posts too
		if re.match ( post_id + "-[\d-]+\.txt",comment ):
			print ( os.path.join( comment_file +" DELETED") )
			os.remove(comment_file)

	post_file = post_id + ".txt"
	# finally delete post
	os.remove( os.path.join(post_directory,post_file) )
	return 

# seaches are directed to this page
# and is rerouted to a URL that can be
# copied and pasted to replicate the search
# searches are case insensitive
@app.route('/search',methods=['POST','GET'])
def search_redirect ():

	# if the user isnt logged in, send them to login page
	if not (session.get('logged_in',0)) or not verify_zid(session.get('zid',0)):
		return redirect ( url_for ( 'login' ) )


	searched_string = request.form.get('searched_string', '')

	return redirect ( url_for ( 'search',searched_string=searched_string ) )


# Shows a list of possible people the student seached for
@app.route('/search/<string:searched_string>', methods=['GET'])
def search ( searched_string ):
	# if the user isnt logged in, send them to login page
	if not (session.get('logged_in',0)) or not verify_zid(session.get('zid',0)):
		return redirect ( url_for ( 'login' ) )

	# retrieve searched string
	search_results = []
	# sort a list of students
	students = sorted(os.listdir(students_dir))

	# check if any names are a substring 
	for student_zid in students:
		# translate zid to string
		student_name = find_name ( student_zid )

		# check if substring exists in name or it matches a zid	
		if re.search(searched_string.lower(),student_name.lower()) or re.match(searched_string.lower(),student_zid.lower()):
			# add possible name to an array of results
			search_results.append(student_zid)

	# search posts that contain searched string
	posts = search_posts_for_string ( searched_string ) 
	# sort the posts by most recent
	post_results = sorted(posts, key=lambda post: post['time'],reverse=True) 

	# return an array of search results containing the substring
	return render_template('search.html', searched_string=searched_string, search_results=search_results, post_results=post_results)


# search posts containing a zid in it's message
# returns an array of posts
def search_posts_for_string (string):
	posts = []
	# iterate over student's folders
	student_zids = os.listdir ( students_dir )	
	for student in student_zids:
		
		files_in_student_folder = os.listdir( os.path.join( students_dir,student ) ) 
		# iterate over files in student's folder
		for post_filename in files_in_student_folder:
		
			# check if current file is a post
			if re.match ( "[\d+-]\.txt",post_filename ):
				post = read_post ( student,post_filename )
				# check if current post mentions a student zid
				if re.search ( string,post['message'].lower() ):
					posts.append (post)	

	return posts

# page for editing profile info
@app.route('/profile/<string:student_zid>/edit',methods=['GET','POST'])
def edit_profile_info ( student_zid ):
	
	# if the user isnt logged in, send them to login page
	if not (session.get('logged_in',0)) or not verify_zid(session.get('zid',0)):
		return redirect ( url_for ( 'login' ) )
	# if user entered invalid student_zid
	if student_zid == '':
		return redirect ( url_for ( '/' ) )

	profile = read_student_profile ( student_zid )

	# check for profile change submission
	if request.form.get('action') != 'SAVE CHANGES':
		return render_template ( 'edit-profile.html',student_profile=profile ) 

	# verify profile changes as valid
	if request.form.get('confirm-password','0') == profile['password']:
		return render_template ('edit-profile.html',student_profile=profile,error="your current password did not match your user")

	# store login profile from the html form
	# for loop not used in case user submits their own html form 
	# if no data was entered, default on previous user settings
	
	full_name = request.form.get('full_name','')
	if full_name == '':
			full_name = profile['full_name']
	print(full_name)
	password = request.form.get('password', '')
	if password == '':
		password = profile['password']
	print(password)
	email = request.form.get('email','')
	if email == '':
		email = profile['email']

	birthday = request.form.get('birthday','')
	if birthday == '':
		birthday = profile['birthday']

	home_suburb = request.form.get('home_suburb','')
	if home_suburb == '':
		home_suburb = profile['home_suburb'] 

	program = request.form.get('program','')
	if program == '':
		program = profile['program']

	courses = request.form.get('courses','')
	if courses == '':
		courses = profile['courses']
		courses = re.sub("[()]","",courses)

	about_me = request.form.get('about_me','')
	if about_me == '':
		about_me = profile['about_me']
	
	# rebuild user account
	create_acccount ( student_zid,password,full_name,email,birthday,home_suburb,program,courses )
	bulk_add_friends (student_zid, profile['friends'])
	write_about_me ( student_zid,about_me )
	
	profile = read_student_profile ( student_zid )
	return render_template ( 'edit-profile.html',student_profile=profile )

# adds a list of zids to a student's account
# used for account editing
def bulk_add_friends ( student_zid,friends ):
	
	# finds the student directory 
	profile_file = os.path.join ( students_dir, student_zid,"student.txt" )
	temp_file = os.path.join ( students_dir, student_zid,"student.tmp" )

	# backup old comment file
	copy ( profile_file,temp_file )

	# prepare new file string
	new_profile_string = ""
	# prepare friends list string
	friends_string = ', '.join(friends)
	with open ( temp_file ) as f:
		old_profile_string = f.read ()
		new_profile_string = re.sub("\nfriends:.*?\n","\nfriends: (" + str(friends_string).strip() + ")\n",old_profile_string )

	os.remove(temp_file)
	# write string to file
	with open ( profile_file,"w" ) as f:
		f.write ( new_profile_string )

	print("FRIENDS ADDED"+new_profile_string+"OVERWRITTEN")

	return


def write_about_me ( student_zid,about_me ):
	# finds the student directory 
	profile_file = os.path.join ( students_dir, student_zid,"student.txt" )
	temp_file = os.path.join ( students_dir, student_zid,"student.tmp" )
	# backup old comment file
	copy ( profile_file,temp_file )
	# prepare new file string
	new_profile_string = ""
	with open ( temp_file ) as f:
		old_profile_string = f.read ()
		new_profile_string = re.sub("\nabout_me:.*?\n","\nabout_me:" + str(about_me).strip() + "\n",old_profile_string )
	os.remove(temp_file)
	# write string to file
	with open ( profile_file,"w" ) as f:
		f.write ( new_profile_string )

	print("ABOUT ME CREATED"+new_profile_string+"OVERWRITTEN")

	return


# page for deleting user account
@app.route('/profile/<string:student_zid>/delete', methods=['GET','POST'])
def delete_page ( student_zid ):

	# if the user isnt logged in, send them to login page
	if not (session.get('logged_in',0)) or not verify_zid(session.get('zid',0)):
		return redirect ( url_for ( 'login' ) )
	# check if user is the owner of the profile
	if not session.get('zid') == student_zid:
		return redirect ( url_for ( 'profile_page',student_zid=student_zid ))
	# check if user has clicked delete button
	if request.method == 'POST':
		user = request.form.get('user') 
		# remove all existence of user
		# user is now dead to this booming social media platform
		if request.form.get('action',0) == 'Delete Account':
			# delete the user account 
			delete_account ( user )
			return redirect ( url_for ( 'logout' ) )
		# talk user down from jumping off
		elif request.form.get('action',0) == 'Return to profile':
			return redirect ( url_for ( 'profile_page',student_zid=user ) )

	student_profile=read_student_profile ( student_zid )
	return render_template('delete-profile.html', student_profile=student_profile)

# deletes a user account
def delete_account ( student_zid ):
	student_directory = os.path.join(students_dir,student_zid)
	try:
		shutil.rmtree(student_directory)
		return 1
	except:
		return -1


# Show student's profile page
@app.route('/profile/<string:student_zid>', methods=['GET','POST'])
def profile_page ( student_zid ):
	# if the user isnt logged in, send them to login page
	if not (session.get('logged_in',0)) or not verify_zid(session.get('zid',0)):
		return redirect ( url_for ( 'login' ) )
	# check if user wanted to add or remove friend
	if request.method == 'POST':
		if request.form.get('action',0) == 'Add Friend':
			user = request.form.get('user')
			add_friend ( user,student_zid )

		elif request.form.get('action',0) == 'Remove Friend':
			user = request.form.get('user')
			remove_friend ( user,student_zid )

	# authenticate user
	is_logged_in ()
	# read student's profile info into a ordered Dict
	student_profile = read_student_profile ( student_zid )
	
	# censor out sensitive data
	for sensitive_data_type in ["email", "courses","home_latitude","home_longitude","password"]:
		student_profile.pop(sensitive_data_type,None)	
	
	# read student's posts into an array of posts ordered by date posted
	student_posts = read_student_posts ( student_zid )
	
	# render the profile page in jinja
	return render_template('profile.html', student_profile=student_profile, student_posts=student_posts)

# check if student A is a friend of student B
# apparently student B doesnt necessarily also have to be student B's friend
def is_friend ( student_A,student_B ):

	student_profile = read_student_profile ( student_A )
	if student_B in student_profile['friends']:
		return 1

	student_profile = read_student_profile ( student_B )
	if student_A in student_profile['friends']:
		return 1
	
	return 0

app.jinja_env.globals.update(is_friend=is_friend)

# adds Student A and Student B as friends 
def add_friend ( student_A,student_B ):
	# find student A's directory
	student_directory = os.path.join ( students_dir,student_A)
	# create path to back up student file
	temp_file = os.path.join(student_directory,"temp.txt")
	# create path to student file
	student_file = os.path.join ( student_directory,"student.txt" )
	# back up student file
	copy ( student_file,temp_file )
	
	newFile = ""
	# create new student file
	with open ( temp_file,'r' ) as f:
	# iterate over lines
		for line in f:
			newline = line
			if "friends:" in line:
				# if friends is empty
				if re.search( 'z\d{7}',line ):
					newline = re.sub ('\)',student_B + ')',line)
				else :
					newline = re.sub ('\)',', ' + student_B + ')',line)
				print (student_A + "adding" + student_B)
				print (line)
				print (newline)
			newFile = newFile + newline
	
	with open ( student_file, 'w+') as s:
		s.write(newFile)
		print (s.read())
	# remove back up file
	
	# find student B's directory
	student_directory = os.path.join ( students_dir,student_B)
	# create path to back up student file
	temp_file = os.path.join(student_directory,"temp.txt")
	# create path to student file
	student_file = os.path.join ( student_directory,"student.txt" )
	# back up student file
	copy ( student_file,temp_file )

	newFile = ""
	# create new student file
	with open ( temp_file,'r' ) as f:
	# iterate over lines
		for line in f:
			newline = line
			if "friends:" in line:
				# if friends is empty
				if re.search( 'z\d{7}',line ):
					newline = re.sub ('\)',student_A + ')',line)
				else :
					newline = re.sub ('\)',', ' + student_A + ')',line)
				print (student_B + "adding" + student_A)
				print (line)
				print (newline)
			newFile = newFile + newline
	
	with open ( student_file, 'w+') as s:
		s.write(newFile)
	# remove back up file

	return 


# remove Student A and Student B as friends 
def remove_friend ( student_A,student_B ):
	print (student_A,student_B)
	print ()
	# find student A's directory
	student_directory = os.path.join ( students_dir,student_A)
	# create path to back up student file
	temp_file = os.path.join(student_directory,"temp.txt")
	# create path to student file
	student_file = os.path.join ( student_directory,"student.txt" )
	# back up student file
	copy ( student_file,temp_file )
	newFile = ""
	# create new student file
	with open ( temp_file,'r' ) as f:
	# iterate over lines
		for line in f:
			newline = line
			if "friends:" in line:
				newline = re.sub ( student_B+"[, ]*",'',line )
				newline = re.sub ('\(, ','',newline )
				newline = re.sub (', \)','',newline )
				print (student_A + "removing" + student_B)
				print (line)
				print (newline)
			newFile = newFile + newline
	
	with open ( student_file, 'w+') as s:
		s.write(newFile)
	# remove back up file
	os.remove (temp_file)	
	
	# find student B's directory
	student_directory = os.path.join ( students_dir,student_B)
	# create path to back up student file
	temp_file = os.path.join(student_directory,"temp.txt")
	# create path to student file
	student_file = os.path.join ( student_directory,"student.txt" )
	# back up student file
	copy ( student_file,temp_file )
	newFile = ""
	# create new student file
	with open ( temp_file,'r' ) as f:
	# iterate over lines
		for line in f:
			newline = line
			if "friends:" in line:
				newline = re.sub ( student_A+"[, ]*",'',line )
				newline = re.sub ('\(, ','',newline )
				newline = re.sub (', \)','',newline )
				print (student_B + "removing" + student_A)
				print (line)	
				print (newline)
			newFile = newFile + newline
	
	with open ( student_file, 'w+') as s:
		s.write(newFile)

	# remove back up file
	os.remove (temp_file)
	return

# verify zid exists in data
def verify_zid ( student_zid ):
	student_folder = os.path.join (students_dir, student_zid)
	if os.path.isdir ( student_folder ):
		return 1
	else:
		return 0


# verify zid and password combination
def verify_password ( student_zid, password ):
	student_profile = read_student_profile ( student_zid )
	if student_profile['password'] == password:
		return 1
	else:
		return 0


# checks if user was already logged in
def is_logged_in ():
	if bool(session.get('logged_in',0)) and session.get('zid',0) != 0 and verify_zid(session.get('zid',0)):
		return 1
	else:
		return redirect ( url_for ( 'login', error="please log in" ) )


# read the student profile file
# return it as a dict (an OrderedDict sorted on name)
def read_student_profile( student_zid ):
	# create folder path we are going to open from 
	student_profile_filename = os.path.join(students_dir, student_zid, "student.txt")

	try: 
	# open file containing the student profile
		with open(student_profile_filename) as f:
			# create an array of profile_info [0] = detail_type, profile_info [1] = detail
			profile_info = [line.strip().split(":",1) for line in f]
	except: 
		print ("PROFILE NOT FOUDN")
		return -1

	# sort the student's profile by the detail thats accessed ie birthday->courses
	sorted_profile = sorted(profile_info, key=lambda profile_info: profile_info[0]) 
	# creates dictionary that remembers the order of profile information
	student_profile = collections.OrderedDict()
	
	# return a dictionary of profile
	for (detail_type, detail) in sorted_profile:
		# create an array of friends under they key 'friends'
		if detail_type == "friends":
			friends = re.split(',', re.sub ('[( )]','',detail ))
			student_profile[detail_type] = friends
		else:
			student_profile[detail_type] = str(detail).strip()
	# ensure student_profile meta is initialised
	detail_types = ['password','email','birthday','home_suburb','program','courses','about_me','friends']
	for detail_type in detail_types:
		if not detail_type in student_profile:
			student_profile['detail_type'] = 'unknown'
			
	# return ordered Dict of a student's profile
	return student_profile



# translates a zid into a full name
def find_name ( student_zid ):
	# create folder path to the student's profile file
	student_profile_filename = os.path.join(students_dir, student_zid, "student.txt")

	# open file
	with open(student_profile_filename) as f:
		for line in f:
			# iterate to the line with the full_name
			if "full_name:" in line:

				return re.sub(r'full_name:','',line).strip()


# add find_name to jinja's environment globals
app.jinja_env.globals.update(find_name=find_name)

	
# read the student's posts
# return an array of dictionaries containing a student's posts
# each array element is a dictionary of post['date'], post['message'] 
# and post['']

def read_student_posts( student_zid ):

	# create folder path to a student's post 
	posts_directory = os.path.join(students_dir, student_zid)
	# create a list of post from the directory
	post_files = sorted(os.listdir( posts_directory ))
	
	# intiialise array of student's posts
	posts = []

	# iterate over student's posts
	for post_filename in post_files:
		# only open posts ie files with [0-9]+.txt
		if re.match("\d+\.txt",post_filename):
			# add post dictionary to the array of studentposts		
			posts.append( read_post( student_zid, post_filename ) )

	# sort the array of posts by most recent first
	posts = sorted(posts, key=lambda post: post['time'], reverse=True) 

	# return an array of dictionaries containing of a student's posts
	return posts

def clickify_zids ( text ):
	# early exit for no zids in post
	if not re.search ( "z\d{7}",str(text) ):
		return text
	new_text = ""
	# extract all zids to teplaces
	zids = re.findall ( "z\d{7}",str(text) )
	unique_zids = []
	# removes duplicate zids in list
	for zid in zids:
		if zid not in unique_zids:
			unique_zids.append ( zid )

	name = find_name (zid)
	for zid in unique_zids:
		# if the zid did not have a user account, dont replace the text
		if not verify_zid (zid):
			next;
		link_string = "<a href=/profile/" + zid + ">" + name + "</a>"
		new_text = re.sub ( zid,link_string,str(text) )
	
	return new_text

app.jinja_env.filters.update(clickify_zids=clickify_zids)



# reads a specific post using a student's zid and a string "NUMBER.txt"
# returns a dictionary keyed by the meta_data e.g post['message'] = comment 
def read_post ( student_zid, post_filename ):

	# create folder path to a student's post 
	posts_directory = os.path.join(students_dir, student_zid)
	# create a list of post from the directory
	post_files = sorted(os.listdir( posts_directory ))
	
	# declare a new dict for the post
	post = {}

	# add post_id attribute to psot
	post['post_id'] = re.sub("\.txt","",post_filename)
	# open file containing the student post
	with open( os.path.join(students_dir, student_zid, post_filename) ) as f:
		# iterate over file	
		for line in f:
			# split by "message :", while preserving message
			(data_type,data) = line.strip().split(': ',1)

			if data_type == "message":
				post['message'] = text_to_markup( data )
			else:
				post[data_type] = data
		
		# add an array of comments to the dictionary
		post['comments'] = read_comments (posts_directory, post_files, post['post_id'] )
	# double check that the post/comment data_types are initialised
	if not 'from' in post:
		post['from'] = student_zid
	if not 'message' in post:
		post['message'] = ' '
	if not 'time' in post:
		post['time'] = '2000-01-01T00:00:00+0000'


	# return a dict
	#print("POST WAS READ "+post_filename+" "+student_zid)
	return post



# converts text special chracters to marked up text
def text_to_markup ( text ) :
	# converts \n's to <br>
	new_text = re.sub (r'\\n','<br>',text)
	return new_text


# converts IS08601 time formatting into a nicer string
# e.g 2016-09-03T02:23:34+0000 to 3rd of September 2016 at 2:32am
def nicefy_time ( date_time ):
	time_struct = dateutil.parser.parse( date_time )
	new_time = time_struct.strftime( "%e of %B %Y at %I:%M%p" )
	return new_time


app.jinja_env.globals.update(nicefy_time=nicefy_time)


# return an array of comments for a student's comment 1 level down
def read_comments ( comments_folder_path, comment_files, post_id ):
	comments = []
	# iterate over files in the student's folder
	for comment_filename in comment_files:
		# check if current file is a comment the post
		if re.match ( post_id+"-[\d]+\.txt", comment_filename ):
			comment = {}
			comment['post_id'] = re.sub("\.txt","",comment_filename)

			# open file containing the comment data
			with open( os.path.join( comments_folder_path, comment_filename) ) as f:
				# iterate over file	
				for line in f:
					# split by "message :", while preserving message
					(data_type,data) = line.strip().split(': ',1)
					if data_type == "message":
						comment['message'] = text_to_markup( data )
					else:
						comment[data_type] = data

			# add replies to the comment
			read_comments ( comments_folder_path, comment_files, comment['post_id'] )
			# add comment dictionary to the array of studentcomments		
			comments.append ( comment )

	# sort the array of comments by oldest first	
	comments = sorted(comments, key=lambda comment: comment['time']) 
	# return an array of dictionaries containing comments related to a post
	return comments

if __name__ == '__main__':
	app.secret_key = os.urandom(12)
	app.run(debug=True, port=46537)
