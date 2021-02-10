import datetime as dt
from calendar import monthrange
from collections import namedtuple, defaultdict

from flask import Flask, render_template, redirect, request, session, flash, jsonify
from flask_user import current_user, login_required, roles_required, roles_accepted, PasswordManager

from application import app, db
from helpers import apology
import models

# Welcome page
@app.route("/")
def index():
    """ TODO """
    if current_user.is_authenticated:
        return redirect("/home")
    else:
        return render_template("index.html")


# The Home page is accessible to any logged-in user
@app.route("/home")
@login_required
def home():
    """ TODO """

    user_roles = [role.name for role in current_user.roles]
    return render_template("home.html", user_roles=user_roles)

# The Requests page is accessible to employees
@app.route("/requests", methods=["GET", "POST"])
@roles_required('Employee')
def requests():
    """ TODO """
    if request.method == 'POST':
        # record from data to database
        user_id = current_user.id
        request_date = dt.datetime.utcnow()
        start_date = dt.datetime.strptime(request.form.get("start_date"), '%Y-%m-%d')
        end_date = dt.datetime.strptime(request.form.get("end_date"), '%Y-%m-%d')
        request_type_name = request.form.get("request_type_name")
        request_type_id = models.RequestType.query.filter(models.RequestType.name == request_type_name).first().id
        prv_note_to_auth = request.form.get("prv_note_to_auth")
        pub_note = request.form.get("pub_note")

        # try to record entries into database
        result = models.create_request(
            user_id = user_id,
            request_date = request_date,
            start_date = start_date,
            end_date = end_date,
            request_type_id = request_type_id,
            prv_note_to_auth = prv_note_to_auth,
            pub_note = pub_note
        )
        # check exit code
        if result == 0:
            flash('Request has been successfully recorded')
        elif result == 1:
            flash('User not found!')
        elif result == 2:
            flash('Invalid dates!')
        elif result == 3:
            flash('Request type not found!')
        else:
            flash('Unknown error occured!')

        return redirect("/requests")

    else:
        # render requests table based on database
        entries = get_requests(current_user)
        requested_days_to_date = get_requested_days_to_date(current_user)
        allowances = get_allowances(current_user)
        request_types =get_request_types()
        return render_template("requests.html", entries=entries, requested_days_to_date=requested_days_to_date, allowances=allowances, request_types=request_types)


# The Authorizations page is accessible to managers and admin
@app.route("/authorizations", methods=["GET", "POST"])
@roles_accepted('Manager', 'Admin')
def authorizations():
    """pass"""

    if request.method == 'POST':
        # record form data to database
        request_id = request.form.get('request_id')
        authorized_string = request.form['acceptOrDecline']
        authorized = (authorized_string == "1")
        prv_note_from_auth = request.form.get('prv_note_from_auth')

        # req = models.UserRequest.query.get(request_id)
        # if req:
        #     req.authorizer_id = current_user.id
        #     req.auth_date = dt.datetime.utcnow()
        #     req.prv_note_from_auth = prv_note_from_auth
        #     req.authorized = authorized
        #     db.session.commit()

        # try to record entries into database
        result = models.authorize_request(
            request_id=request_id,
            authorizer_id=current_user.id,
            prv_note_from_auth=prv_note_from_auth,
            authorized=authorized
        )
        # check exit code
        if result == 0:
            flash(f'Request has been successfully {"authorized" if authorized else "declined"}')
        elif result == 1:
            flash('Request not found!')
        elif result == 2:
            flash('Authorizer not found!')
        elif result == 3:
            flash('Invalid authorization status!')
        else:
            flash('Unknown error occured!')

        return redirect("/authorizations")

    else:
        # render authorizations table based on database
        entries = get_authorizations(current_user)
        return render_template("authorizations.html", entries=entries)


# The Calendar page is accessible to employee, managers, hr and admin
@app.route("/calendar")
@roles_accepted('Manager', 'Employee', 'HR', 'Admin')
def calendar():
    """pass"""

    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    if not (date_from and date_to):
        d = dt.datetime.today()
        date_from = d.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        date_to = dt.datetime(d.year, d.month, monthrange(d.year, d.month)[-1]) + dt.timedelta(days=1)
    else:
        date_from = dt.datetime.strptime(date_from, "%Y-%m-%d")
        date_to = dt.datetime.strptime(date_to, "%Y-%m-%d")

    # get entries to show based on current user's roles
    entries = get_calendar_entries(current_user, date_from, date_to)
    calendar_days, calendar_rows = tabularize_calendar(entries, date_from, date_to)
    return render_template(
        "calendar.html",
        calendar_days=calendar_days,
        calendar_rows=calendar_rows,
        date_from=date_from.strftime("%Y-%m-%d"),
        date_to=date_to.strftime("%Y-%m-%d")
    )


# The Administration page is accessible to looged in users
@app.route("/administration")
@login_required
def administration():
    """pass"""

    user_roles = [role.name for role in current_user.roles]
    return render_template("administration.html", user_roles=user_roles)


# The Password change page is accessible to logged-in users
@app.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    """ Change user password """
    return app.user_manager.change_password_view()


# The Add user page is accessible to hr and admin
@app.route("/add_user", methods=["GET", "POST"])
@roles_accepted('HR', 'Admin')
def add_user():
    """ Add new user """

    roles_selected = [] # init list

    if request.method == 'POST':
        # record from data to database
        username = request.form.get("username")
        pwd_raw1 = request.form.get("password")
        pwd_raw2 = request.form.get("retype_password")
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        superior = request.form.get("superior") # format: '{id} {first_name} {last_name}'
        superior_id = int(superior.split()[0]) if superior else None
        roles_selected = request.form.getlist('roles')

        # check passwords
        if pwd_raw1 == pwd_raw2:

            # try to record entries into database
            result = models.create_user(
                username=username,
                password=pwd_raw1,
                first_name=first_name,
                last_name=last_name,
                superior_id=superior_id,
                roles=roles_selected
            )
            # check exit code
            if result == 0:
                flash('User has been successfully registered')
                return redirect('/add_user')
            elif result == 1:
                flash('Username already exists!')
            elif result == 2:
                flash('Invalid password!')
            else:
                flash('Unknown error occured!')

        else:
            flash('Passwords do not match')

    # GET request or inappropriate POST request: render form
    managers = get_managers()
    roles = get_roles()
    if not roles_selected:
        roles_selected = ['Employee',] # default value: Employee

    return render_template("add_user.html", managers=managers, roles=roles, roles_selected=roles_selected)


# The Update user page is accessible to hr and admin
@app.route("/update_user", methods=["GET", "POST"])
@roles_accepted('HR', 'Admin')
def update_user():
    """ Update an existing user """

    roles_selected = [] # init list

    if request.method == 'POST':
        # record from data to database
        user_id = request.form.get("user_id")
        active = 'active' in request.form
        username = request.form.get("username")
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        superior = request.form.get("superior") # format: '{id} {first_name} {last_name}'
        superior_id = int(superior.split()[0]) if superior else None
        roles_selected = request.form.getlist('roles')

        user = models.User.query.get(user_id)


        # try to record entries into database
        result = models.update_user(
            user_id=user_id,
            active=active,
            username=username,
            first_name=first_name,
            last_name=last_name,
            superior_id=superior_id,
            roles=roles_selected
        )
        # check exit code
        if result == 0:
            flash('User has been successfully updated')
            return redirect('/update_user')
        elif result == 1:
            flash('User not found!')
        else:
            flash('Unknown error occured!')

    # GET request or inappropriate POST request: render form
    users = get_users()
    managers = get_managers()
    roles = get_roles()

    return render_template("update_user.html", users=users, managers=managers, roles=roles)


# The Query user page is accessible to hr and admin
@app.route("/query_user", methods=["POST"])
@roles_accepted('HR', 'Admin')
def query_user():
    """Responds to ajax post request: returns data of a user"""

    selected_user = request.json['user']
    user_id = int(selected_user.split()[0])
    user = models.User.query.get(user_id)

    # resolve superior
    superior = models.User.query.get(user.superior_id) if user.superior_id else None

    user_data = {
        'user_id'       :   user.id,
        'active'        :   user.active,
        'username'      :   user.username,
        'first_name'    :   user.first_name,
        'last_name'     :   user.last_name,
        'superior'      :   get_id_name(superior),
        'roles'         :   [role.name for role in user.roles],
        'allowances'    :   get_allowances(user)
    }

    response = jsonify(user_data)
    return response


# The Add Request Type page is accessible to hr and admin
@app.route("/add_request_type", methods=["GET", "POST"])
@roles_accepted('HR', 'Admin')
def add_request_type():
    """ Add new request type """

    if request.method == 'POST':

        # record from data to database
        request_type_name = request.form.get("request_type_name")
        print(request_type_name)

        # try to record entries into database
        result = models.create_request_type(
            name=request_type_name,
        )
        # check exit code
        if result == 0:
            flash('Request type has been successfully recorded')
            return redirect('/add_request_type')
        elif result == 1:
            flash('Request type already exists!')
        elif result == 2:
            flash('Invalid request type name!')
        else:
            flash('Unknown error occured!')

    # GET request or inappropriate POST request: render form
    entries = get_request_types(names_only=False)
    return render_template("add_request_type.html", entries=entries)


# The Allowances page is accessible to hr and admin
@app.route("/update_allowances", methods=["GET", "POST"])
@roles_accepted('HR', 'Admin')
def update_allowances():
    """ Add or modify allowances """

    if request.method == 'POST':
        # record from data to database
        user_id = request.form.get("user_id")

        # iterate request types
        error_found = False
        for rt in models.RequestType.query.all():
            request_type_id = rt.id
            request_type_name = rt.name
            allowance = request.form.get(str(request_type_id))

            # try to record entries into database
            result = models.update_allowance(
                user_id=user_id,
                request_type_id=request_type_id,
                allowance_days=int(allowance)
            )
            # check exit code
            if result == 0:
                flash(f'Allowance for {request_type_name} has been successfully recorded')
            elif result == 1:
                flash(f'Allowance for {request_type_name} has not been changed')
            elif result == 2:
                error_found = True
                flash('User not found!')
            elif result == 3:
                error_found = True
                flash(f"Request type '{request_type_name}' not found!")
            elif result == 4:
                error_found = True
                flash(f"Invalid entry for '{request_type_name}'")
            else:
                error_found = True
                flash('Unknown error occured!')

        if not error_found:
            return redirect('/update_allowances')

    # GET request or inappropriate POST request: render form
    users = get_users()
    return render_template("update_allowances.html", users=users)


# The Query allowances page is accessible to hr and admin
@app.route("/query_allowances", methods=["POST"])
@roles_accepted('HR', 'Admin')
def query_allowances():
    """Responds to ajax post request: returns allowances of a user"""

    selected_user = request.json['user']
    user_id = int(selected_user.split()[0])
    user = models.User.query.get(user_id)

    allowances = get_allowances(user, names_only=False)

    response = jsonify(allowances)
    return response


def get_requests(user):
    """
    Returns requests of a user.

    @param user         instance of User class
    @return             list of named tuples
    """

    # define structure
    entries = []
    Entry = namedtuple('Entry', [
        'request_date',
        'start_date',
        'end_date',
        'request_type',
        'prv_note_to_auth',
        'prv_note_from_auth',
        'pub_note',
        'status'
        ])

    # get user requests
    user_requests = user.requests
    for req in user_requests:
        request_date = f'{req.request_date:%Y-%m-%d}'
        start_date = f'{req.start_date:%Y-%m-%d}'
        end_date = f'{req.end_date:%Y-%m-%d}'
        request_type = req.request_type.name
        prv_note_to_auth = req.prv_note_to_auth
        prv_note_from_auth = req.prv_note_from_auth
        pub_note = req.pub_note
        if req.authorized and req.auth_date:
            status = f'Authorized by {req.authorizer.username} on {req.auth_date:%Y-%m-%d}'
        elif req.auth_date:
            status = f'Declined by {req.authorizer.username} on {req.auth_date:%Y-%m-%d}'
        else:
            status = f'Waiting for Approval'
        e = Entry(
                request_date = request_date,
                start_date = start_date,
                end_date = end_date,
                request_type = request_type,
                prv_note_to_auth = prv_note_to_auth,
                prv_note_from_auth = prv_note_from_auth,
                pub_note = pub_note,
                status = status
        )
        entries.append(e)

    return entries


def get_requested_days_to_date(user):
    """
    Returns requested days to date of a user.

    @param user         instance of User class
    @return             dictionary {request_type : requested days}
    """

    # define structure: fill with 0 default values
    requested_days = {rt : 0 for rt in get_request_types()}

    user_requests = user.requests
    for req in user_requests:
        rtype = req.request_type.name
        days = (req.end_date - req.start_date).days + 1
        requested_days[rtype] += days

    return requested_days


def get_allowances(user, names_only=True):
    """
    Returns allowance days to date of a user.

    @param user         instance of User class
    @param names_only   determines the structure of returned data
    @return             if names_only=False -> dictionary {request_type_id : list(request_type_name, allowance days)}
                        if names_only=True -> dictionary {request_type_name : allowance days}
    """

    # define structure: fill with 0 default values
    if names_only:
        allowances = {rt : 0 for rt in get_request_types(names_only=names_only)}
    else:
        allowances = {rt.id: [rt.name, 0] for rt in get_request_types(names_only=names_only)}


    # get user allowances
    user_allowances = user.allowances
    for ua in user_allowances:
        rtype_id = ua.request_type.id
        rtype_name = ua.request_type.name
        days = ua.days
        if names_only:
            allowances[rtype_name] = days
        else:
            allowances[rtype_id][1] = days

    return allowances


def get_request_types(names_only=True):
    """
    Returns list of request types.

    @param names_only   determines the structure of returned data
    @return             list of request types
    """

    request_types = []
    #query database
    qry = models.RequestType.query.all()

    if names_only:
        request_types = [rt.name for rt in qry]

    else:
        # define named tuple
        Entry = namedtuple('Entry', [
            'id',
            'name'
            ])
        #populate list
        for rt in qry:
            id = rt.id
            name=rt.name
            e = Entry(
                    id = id,
                    name = name,
            )
            request_types.append(e)

    return request_types


def get_roles():
    """
    Returns list of roles.

    @return             list of roles
    """

    roles = [r.name for r in models.Role.query.all()]
    return roles


def get_managers():
    """
    Returns list of managers.

    @return             list of managers: id and full name
    """

    managers = []
    users = models.User.query.all()
    for user in users:
        roles = [r.name for r in user.roles]
        if 'Manager' in roles:
            managers.append(get_id_name(user))

    return managers


def get_users():
    """
    Returns list of users.

    @return             list of users: id and full name
    """

    users = []
    qry = models.User.query.all()
    for user in qry:
        users.append(get_id_name(user))

    return users


def get_authorizations(user):
    """
    Returns items to authorize by a user.

    @param user         instance of User class
    @return             list of named tuples
    """

    # define structure
    entries = []
    Entry = namedtuple('Entry', [
        'id',
        'user_id',
        'name',
        'request_date',
        'start_date',
        'end_date',
        'request_type',
        'prv_note_to_auth',
        'prv_note_from_auth',
        'pub_note',
        'status'
        ])

    # get user approvals
    user_authorizations = models.UserRequest.query.\
        filter(models.UserRequest.user.has(superior_id = user.id)).\
        filter(models.UserRequest.auth_date.is_(None)).\
        all()
    for req in user_authorizations:
        id = req.id
        user_id = req.user_id
        user_name = f'{req.user.first_name} {req.user.last_name}'
        request_date = f'{req.request_date:%Y-%m-%d}'
        start_date = f'{req.start_date:%Y-%m-%d}'
        end_date = f'{req.end_date:%Y-%m-%d}'
        request_type = req.request_type.name
        prv_note_to_auth = req.prv_note_to_auth
        prv_note_from_auth = req.prv_note_from_auth
        pub_note = req.pub_note
        if req.authorized and req.auth_date:
            status = f'Authorized by {req.authorizer.username} on {req.auth_date:%Y-%m-%d}'
        elif req.auth_date:
            status = f'Declined by {req.authorizer.username} on {req.auth_date:%Y-%m-%d}'
        else:
            status = f'Waiting for Approval'
        e = Entry(
                id = id,
                user_id = user_id,
                name = user_name,
                request_date = request_date,
                start_date = start_date,
                end_date = end_date,
                request_type = request_type,
                prv_note_to_auth = prv_note_to_auth,
                prv_note_from_auth = prv_note_from_auth,
                pub_note = pub_note,
                status = status
        )
        entries.append(e)

    return entries


def get_calendar_entries(user, date_from, date_to):
    """
    Returns calendar entries of a user.

    @param user         instance of User class
    @param date_from    start date of period to query (datetime)
    @param date_to      end date of period to query (datetime)
    @return             list of named tuples
    """

    entries = []

    # get role
    user_roles = [role.name for role in user.roles]

    # admin can view everybody's entries
    if 'Admin' in user_roles:
        print("I'm Admin")
        # qry = db.session.query(models.User).\
        #     outerjoin(models.UserRequest, models.User.id == models.UserRequest.user_id).\
        #     all()
        sub_qry = db.session.query(models.UserRequest).subquery()
        req = db.aliased(models.UserRequest, sub_qry)
        qry = db.session.query(models.User, req).\
            outerjoin(sub_qry, req.user_id == models.User.id).\
            all()
        entries = get_calendar_entries_from_qry(qry)
    else:

        # employee can view own entries
        if 'Employee' in user_roles:
            print("I'm an employee")
            sub_qry = db.session.query(models.UserRequest).subquery()
            req = db.aliased(models.UserRequest, sub_qry)
            qry = db.session.query(models.User, req).\
                outerjoin(sub_qry, req.user_id == models.User.id).\
                filter(models.User.id == user.id).\
                all()
            entries += get_calendar_entries_from_qry(qry)

        # manager can view its team's entries as well
        if 'Manager' in user_roles:
            print("I'm a manager")
            sub_qry = db.session.query(models.UserRequest).subquery()
            req = db.aliased(models.UserRequest, sub_qry)
            qry = db.session.query(models.User, req).\
                outerjoin(sub_qry, req.user_id == models.User.id).\
                filter(models.User.superior_id == user.id).\
                all()
            entries += get_calendar_entries_from_qry(qry)

        # hr can view everybody else's approved entries
        if 'HR' in user_roles:
            print("I'm HR")
            sub_qry = db.session.query(models.UserRequest).filter(models.UserRequest.authorized == True).subquery()
            req = db.aliased(models.UserRequest, sub_qry)
            qry = db.session.query(models.User, req).\
                outerjoin(sub_qry, req.user_id == models.User.id).\
                filter(models.User.id != user.id).\
                filter(db.or_(models.User.superior_id != user.id, models.User.superior_id.is_(None))).\
                all()
            entries += get_calendar_entries_from_qry(qry)

    return entries


def get_calendar_entries_from_qry(qry):
    """
    Returns list of calendar entries from the given query object.

    @param qry          SQLAlchemy Query object
    @return             list of named tuples
    """

    # define structure
    entries = []
    Entry = namedtuple('Entry', [
        'id',
        'user_id',
        'name',
        'request_date_str',
        'start_date_str',
        'end_date_str',
        'request_date',
        'start_date',
        'end_date',
        'request_type',
        'prv_note_to_auth',
        'prv_note_from_auth',
        'pub_note',
        'request_class'
        ])

    # parse user requests
    for user, req in qry:
        user_id = user.id
        user_name = f'{user.first_name} {user.last_name}'
        if not req:
            e = Entry(
                    id = None,
                    user_id = user_id,
                    name = user_name,
                    request_date_str = None,
                    start_date_str = None,
                    end_date_str = None,
                    request_date = None,
                    start_date = None,
                    end_date = None,
                    request_type = None,
                    prv_note_to_auth = None,
                    prv_note_from_auth = None,
                    pub_note = None,
                    request_class = None
            )
            entries.append(e)
        else:
            id = req.id
            request_date_str = f'{req.request_date:%Y-%m-%d}'
            start_date_str = f'{req.start_date:%Y-%m-%d}'
            end_date_str = f'{req.end_date:%Y-%m-%d}'
            request_date = req.request_date
            start_date = req.start_date
            end_date = req.end_date
            request_type = req.request_type.name
            prv_note_to_auth = req.prv_note_to_auth
            prv_note_from_auth = req.prv_note_from_auth
            pub_note = req.pub_note
            if req.authorized and req.auth_date:
                request_class = "requestAuthorized"
            elif req.auth_date:
                request_class = "requestDeclined"
            else:
                request_class = "requestWaitingForApproval"
            e = Entry(
                    id = id,
                    user_id = user_id,
                    name = user_name,
                    request_date_str = request_date_str,
                    start_date_str = start_date_str,
                    end_date_str = end_date_str,
                    request_date = request_date,
                    start_date = start_date,
                    end_date = end_date,
                    request_type = request_type,
                    prv_note_to_auth = prv_note_to_auth,
                    prv_note_from_auth = prv_note_from_auth,
                    pub_note = pub_note,
                    request_class = request_class
            )
            entries.append(e)

    return entries


def tabularize_calendar(entries, date_from, date_to):

    # init data structures
    calendar_days = []
    calendar_rows = {}

    # populate calendar days
    for d in daterange(date_from, date_to):
        calendar_days.append(str(d.day).zfill(2)) # add leading zero

    # populate calendar rows
    for entry in entries:
        # get Entry info
        user_id = entry.user_id
        name = entry.name
        start_date = entry.start_date
        end_date = entry.end_date
        # initialize dictionary, if needed
        if not user_id in calendar_rows:
            data = [None]*len(calendar_days)
            calendar_rows[user_id] = [name, data]

        # tabularise data (only if we have records)
        if not (start_date is None or end_date is None):
            for count, d in enumerate(daterange(date_from, date_to)):
                if (start_date <= d <= end_date):
                    calendar_rows[user_id][1][count] = entry

    return (calendar_days, calendar_rows)



def daterange(date1, date2):
    for n in range(int((date2 - date1).days)):
        yield date1 + dt.timedelta(n)


def get_id_name(user):
    """
    Returns string representation of a user in form
    {user.id} {user.first_name} {user.last_name}
    """
    if user:
        return(f'{user.id} {user.first_name} {user.last_name}')