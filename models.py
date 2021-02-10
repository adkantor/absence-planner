import datetime as dt
import re

from flask_user import UserManager, UserMixin

from application import app, db


class User(db.Model, UserMixin):
    """Define the User data-model."""
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    active = db.Column('is_active', db.Boolean(), nullable=False, server_default='1')

    # User authentication information. The collation='NOCASE' is required
    # to search case insensitively when USER_IFIND_MODE is 'nocase_collation'.
    username = db.Column(db.String(100, collation='NOCASE'), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False, server_default='')

    # User information
    first_name = db.Column(db.String(100, collation='NOCASE'), nullable=False, server_default='')
    last_name = db.Column(db.String(100, collation='NOCASE'), nullable=False, server_default='')

    # Hierarchy
    superior_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE'))
    subordinates = db.relationship('User', backref=db.backref('superior', remote_side=[id]))

    # Define the relationship to Role via UserRole
    roles = db.relationship('Role', secondary='user_roles')
    # Define relationship to Allowance
    allowances = db.relationship('Allowance')


class Role(db.Model):
    """Define the Role data-model"""
    __tablename__ = 'roles'
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(50), unique=True)


class UserRole(db.Model):
    """Define the User-Role association table"""
    __tablename__ = 'user_roles'
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE'))
    role_id = db.Column(db.Integer(), db.ForeignKey('roles.id', ondelete='CASCADE'))


class UserRequest(db.Model):
    """Define the UserRequest data-model"""
    __tablename__ = 'user_requests'
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE'))
    authorizer_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE'))
    request_date = db.Column(db.DateTime())
    auth_date = db.Column(db.DateTime())
    start_date = db.Column(db.DateTime())
    end_date = db.Column(db.DateTime())
    request_type_id = db.Column(db.Integer(), db.ForeignKey('request_types.id', ondelete='CASCADE'))
    prv_note_to_auth = db.Column(db.UnicodeText(255), server_default='')
    prv_note_from_auth = db.Column(db.UnicodeText(255), server_default='')
    pub_note = db.Column(db.UnicodeText(255), server_default='')
    authorized = db.Column('is_authorized', db.Boolean(), nullable=False, server_default='0')

    # Define relationships to User
    user = db.relationship('User', backref='requests', foreign_keys=[user_id])
    authorizer = db.relationship('User', backref='authorizations', foreign_keys=[authorizer_id])
    # Define relationship to RequestType
    request_type = db.relationship('RequestType', backref='user_requests')
    # Define relationship to Allowance
    allowance = db.relationship('Allowance',
                                primaryjoin='and_(foreign(UserRequest.user_id) == remote(Allowance.user_id), foreign(UserRequest.request_type_id) == remote(Allowance.request_type_id))',
                                backref='user_requests'
    )


class Allowance(db.Model):
    """Define the Allowance data-model"""
    __tablename__ = 'allowances'
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('users.id', ondelete='CASCADE'))
    request_type_id = db.Column(db.Integer(), db.ForeignKey('request_types.id', ondelete='CASCADE'))
    days = db.Column(db.Integer())

    # Define relationship to RequestType
    request_type = db.relationship('RequestType', backref='allowances')


class RequestType(db.Model):
    """Define the RequestType data-model"""
    __tablename__ = 'request_types'
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(50), unique=True)


def get_user_by_username(username):
    return User.query.filter(User.username == 'username').first()


def create_request(user_id, request_date, start_date, end_date,
                   request_type_id, prv_note_to_auth='', pub_note=''):
    """
    Creates a new request.

    Exit codes:
    0: success
    1: user not found
    2: invalid dates
    3: request type not found
    4: unknown error
    """

    # check user exists
    user = User.query.get(user_id)
    if not user: return 1
    # check dates
    if not isinstance(request_date, dt.datetime): return 2
    if not isinstance(start_date, dt.datetime): return 2
    if not isinstance(end_date, dt.datetime): return 2
    if not (end_date >= start_date): return 2
    # check request type exists
    rtype = RequestType.query.get(request_type_id)
    if not rtype: return 3

    req = UserRequest(
        request_date = request_date,
        start_date = start_date,
        end_date = end_date,
        request_type_id = request_type_id,
        prv_note_to_auth = prv_note_to_auth,
        pub_note = pub_note,
    )
    try:
        user.requests.append(req)
        db.session.commit()
    except:
        pass
    else:
        return 0

    return 4


def authorize_request(request_id, authorizer_id, prv_note_from_auth='', authorized=False):
    """
    Authorizes a new request.

    Exit codes:
    0: success
    1: request not found
    2: user (authorizer) not found
    3: invalid status
    4: unknown error
    """

    # check request exists
    req = UserRequest.query.get(request_id)
    if not req: return 1
    # check authorier exists
    authorizer = User.query.get(authorizer_id)
    if not authorizer: return 2
    # check authorized status
    if not isinstance(authorized, int): return 3
    if not (authorized == 1 or authorized == 0): return 3

    try:
        req.authorizer_id = authorizer_id
        req.auth_date = dt.datetime.utcnow()
        req.prv_note_from_auth = prv_note_from_auth
        req.authorized = authorized
        db.session.commit()
    except:
        pass
    else:
        return 0

    return 4


def create_user(username='', password='',
                first_name='', last_name='',
                superior_id=None, roles=[]):
    """
    Creates a new user.

    Exit codes:
    0: success
    1: username already exists
    2: invalid password
    3: unknown error
    """

    if not User.query.filter(User.username == username).first():
        if (len(password) < 1) or (re.search(r"\s", password)):
            # password is empty or contains whitespace
            return 2

        try:
            user = User(
                username=username,
                password=user_manager.hash_password(password),
                first_name = first_name,
                last_name = last_name,
                superior_id = superior_id
            )
            user.roles = [Role.query.filter(Role.name == r).first() for r in roles]
            db.session.add(user)
            db.session.commit()
        except:
            pass
        else:
            return 0
    else:
        return 1

    return 3


def update_user(user_id=None, active=False, username='',
                first_name='', last_name='',
                superior_id=None, roles=[]):
    """
    Updates an existing user.

    Exit codes:
    0: success
    1: user not found
    2: unknown error
    """

    user = User.query.get(user_id)
    if not user:
        return 1

    try:
        user.active = active
        user.username = username
        user.first_name = first_name
        user.last_name = last_name
        user.superior_id = superior_id
        user.roles = [Role.query.filter(Role.name == r).first() for r in roles]
        db.session.commit()
    except:
        pass
    else:
        return 0

    return 2


def create_request_type(name=''):
    """
    Creates a new request type.

    Exit codes:
    0: success
    1: name already exists
    2: invalid name
    3: unknown error
    """
    # check name
    if len(name) < 1 or name.isspace():
        return 2

    if not RequestType.query.filter(RequestType.name == name).first():

        try:
            rt = RequestType(name=name)
            db.session.add(rt)
            db.session.commit()
        except:
            pass
        else:
            return 0
    else:
        return 1

    return 3


def get_role_by_name(role_name):
    return Role.query.filter(Role.name == role_name).first()


def update_allowance(user_id, request_type_id, allowance_days):
    """
    Updates allowance of a user (creates records, if needed).

    Exit codes:
    0: success
    1: no change needed
    2: user not found
    3: request type not found
    4: invalid allowance days
    5: unknown error
    """

    # check user exists
    user = User.query.get(user_id)
    if not user:
        return 2
    # check request type exists
    if not RequestType.query.get(request_type_id):
        return 3
    # check allowance days
    if not isinstance(allowance_days, int):
        return 4
    if allowance_days < 0:
        return 4

    allowance = Allowance.query.filter(Allowance.user_id == user_id, Allowance.request_type_id == request_type_id).first()

    if allowance:
        # user_id - request_type_id combination exists -> update
        if allowance.days == allowance_days:
            # days has not been changed
            return 1
        try:
            allowance.days = allowance_days
            db.session.commit()
        except:
            pass
        else:
            return 0

    else:
        # combination does not exist -> append new record
        try:
            user.allowances.append(Allowance(request_type_id=request_type_id, days=allowance_days))
            db.session.commit()
        except:
            pass
        else:
            return 0

    return 5


# Setup Flask-User and specify the User data-model
user_manager = UserManager(app, db, User)


def create_db():
    """Create all database tables"""
    db.create_all()


def create_demo_users():
    """Create some demo users"""

    # Create roles
    finance =  Role.query.filter(Role.name == 'Finance').first()
    if not finance:
        finance = Role(name='Finance')

    marketing = Role.query.filter(Role.name == 'Marketing').first()
    if not marketing:
        marketing = Role(name='Marketing')

    employee = Role.query.filter(Role.name == 'Employee').first()
    if not employee:
        employee = Role(name='Employee')

    manager = Role.query.filter(Role.name == 'Manager').first()
    if not manager:
        manager = Role(name='Manager')

    hr = Role.query.filter(Role.name == 'HR').first()
    if not hr:
        hr = Role(name='HR')

    admin = Role.query.filter(Role.name == 'Admin').first()
    if not admin:
        admin = Role(name='Admin')


    # Create 'finance manager' user: can view and approve whole finance, but edit only own data
    if not User.query.filter(User.username == 'finman').first():
        user = User(
            username='finman',
            first_name = "John",
            last_name = "Smith",
            password=user_manager.hash_password('Password1'),
        )
        user.roles = [finance, employee, manager]
        db.session.add(user)
        db.session.commit()

    # Create 'marketing manager' user: can view and approve whole marketing, but edit only own data
    if not User.query.filter(User.username == 'markman').first():
        user = User(
            username='markman',
            first_name = "Jane",
            last_name = "Woo",
            password=user_manager.hash_password('Password1'),
        )
        user.roles = [marketing, employee, manager]
        db.session.add(user)
        db.session.commit()

    # Create 'finance employee' user: can view whole finance but edit only own data
    if not User.query.filter(User.username == 'finemp').first():
        user = User(
            username='finemp',
            first_name = "John",
            last_name = "Doe",
            password=user_manager.hash_password('Password1'),
            superior_id=1,
        )
        user.roles = [finance, employee]
        db.session.add(user)
        db.session.commit()

    # Create 'marketing employee' user: can view whole marketing but edit only own data
    if not User.query.filter(User.username == 'markemp').first():
        user = User(
            username='markemp',
            first_name = "Jane",
            last_name = "Smith",
            password=user_manager.hash_password('Password1'),
            superior_id=2,
        )
        user.roles = [marketing, employee]
        db.session.add(user)
        db.session.commit()

    # Create 'hr' user: can view all
    if not User.query.filter(User.username == 'hr').first():
        user = User(
            username='hr',
            first_name = "Harold",
            last_name = "Smith",
            password=user_manager.hash_password('Password1'),
        )
        user.roles = [hr, employee]
        db.session.add(user)
        db.session.commit()

    # Create 'admin' user with 'Admin' role
    if not User.query.filter(User.username == 'admin').first():
        user = User(
            username='admin',
            first_name = "Admin",
            last_name = "Admin",
            password=user_manager.hash_password('Password1'),
        )
        user.roles = [admin,]
        db.session.add(user)
        db.session.commit()


def create_demo_request_types():
    """Create some demo request types"""

    # Create 'holiday'
    if not RequestType.query.filter(RequestType.name == 'holiday').first():
        rtype = RequestType(
            name='holiday'
        )
        db.session.add(rtype)
        db.session.commit()

    # Create 'sick'
    if not RequestType.query.filter(RequestType.name == 'sick').first():
        rtype = RequestType(
            name='sick'
        )
        db.session.add(rtype)
        db.session.commit()


def create_demo_allowances():
    """Create some demo allowances"""

    if not Allowance.query.filter(Allowance.user_id == 1, Allowance.request_type_id == 1).first():
        allowance = Allowance(
            user_id = 1,
            request_type_id = 1,
            days = 25
        )
        db.session.add(allowance)
        db.session.commit()

    if not Allowance.query.filter(Allowance.user_id == 2, Allowance.request_type_id == 1).first():
        allowance = Allowance(
            user_id = 2,
            request_type_id = 1,
            days = 26
        )
        db.session.add(allowance)
        db.session.commit()

    if not Allowance.query.filter(Allowance.user_id == 3, Allowance.request_type_id == 1).first():
        allowance = Allowance(
            user_id = 3,
            request_type_id = 1,
            days = 27
        )
        db.session.add(allowance)
        db.session.commit()

    if not Allowance.query.filter(Allowance.user_id == 4, Allowance.request_type_id == 1).first():
        allowance = Allowance(
            user_id = 4,
            request_type_id = 1,
            days = 28
        )
        db.session.add(allowance)
        db.session.commit()


def create_demo_requests():
    """Create some demo requests"""

    if not UserRequest.query.filter(UserRequest.user_id == 1).first():
        req = UserRequest(
            user_id = 1,
            authorizer_id = 3,
            request_date = dt.datetime(2020,7,1),
            # auth_date =
            start_date = dt.datetime(2020,8,1),
            end_date = dt.datetime(2020,8,10),
            request_type_id = 1,
            prv_note_to_auth = 'Private note to the authorizer',
            # prv_note_from_auth =
            pub_note = 'This is a public note',
            # authorized =
        )
        db.session.add(req)
        db.session.commit()


# create_db()
# create_demo_users()
# create_demo_request_types()
# create_demo_allowances()
# create_demo_requests()