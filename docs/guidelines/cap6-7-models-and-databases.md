6 | Model Best Practices

Models are the foundation of most Django projects. Racing to write Django models without

thinking things through can lead to problems down the road.

All too frequently we developers rush into adding or modifying models without considering

the ramifications of what we are doing. The quick fix or sloppy “temporary” design decision

that we toss into our codebase now can hurt us in the months or years to come, forcing crazy

workarounds or corrupting existing data.

So keep this in mind when adding new models in Django or modifying existing ones. Take

your time to think things through, and design your foundation to be as strong and sound as

possible.

PACKAGE TIP: Our Picks for Working With Models

Here’s a quick list of the model-related Django packages that we use in practically

every project.

(cid:228) django-model-utils to handle common patterns like TimeStampedModel.

(cid:228) django-extensions has

a powerful management

command called

shell_plus which autoloads the model classes for all

installed apps.

The downside of this library is that it includes a lot of other functionality

which breaks from our preference for small, focused apps.

6.1 Basics

6.1.1 Break Up Apps With Too Many Models

If there are 20+ models in a single app, think about ways to break it down into smaller apps,

as it probably means your app is doing too much. In practice, we like to lower this number

to no more than five to ten models per app.

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

63

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 11322Chapter 6: Model Best Practices

6.1.2 Be Careful With Model Inheritance

Model inheritance in Django is a tricky subject. Django provides three ways to do model

inheritance: abstract base classes, multi-table inheritance, and proxy models.

WARNING: Django Abstract Base Classes <> Python Abstract
Base Classes

Don’t confuse Django abstract base classes with the abstract base classes in the

Python standard library’s abc module, as they have very different purposes and be-

haviors.

Here are the pros and cons of the three model inheritance styles. To give a complete com-

parison, we also include the option of using no model inheritance to begin with:

Model Inheritance Style
No model
if
inheritance:
models have a common
field, give both models that
field.
Abstract base classes: tables
are only created for derived
models.

Multi-table
inheritance:
tables are created for both
child. An
parent
implied OneToOneField
links parent and child.

and

Proxy models: a table is
only created for the original
model.

Pros
Makes
to un-
it easiest
derstand at a glance how
Django models map to
database tables.
Having the common fields
in an abstract parent class
saves us from typing them
more than once.
We don’t get
the over-
head of extra tables and
joins that are incurred from
multi-table inheritance.
Gives each model its own
table, so that we can query
child
either
model.
It also gives us the abil-
ity to get to a child ob-
ject from a parent object:
parent.child
Allows us to have an alias
of a model with different
Python behavior.

parent

or

Cons
If there are a lot of fields du-
plicated across models, this
can be hard to maintain.

We cannot use the parent
class in isolation.

Adds substantial overhead
since each query on a child
table requires joins with all
parent tables.
We strongly recommend
against using multi-table
inheritance. See the warn-
ing below.
We
model’s fields.

change

cannot

the

Table 6.1: Pros and Cons of the Model Inheritance Styles

64

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 113226.1: Basics

WARNING: Avoid Multi-Table Inheritance

Multi-table inheritance, sometimes called “concrete inheritance,” is considered by

the authors and many other developers to be a bad thing. We strongly recommend

against using it. We’ll go into more detail about this shortly.

Here are some simple rules of thumb for knowing which type of inheritance to use and

when:

(cid:228) If the overlap between models is minimal (e.g. you only have a couple of models

that share one or two identically named fields), there might not be a need for model

inheritance. Just add the fields to both models.

(cid:228) If there is enough overlap between models that maintenance of models’ repeated fields

cause confusion and inadvertent mistakes, then in most cases the code should be

refactored so that the common fields are in an abstract base model.

(cid:228) Proxy models are an occasionally-useful convenience feature, but they’re very different

from the other two model inheritance styles.

(cid:228) At all costs, everyone should avoid multi-table inheritance (see warning above) since

it adds both confusion and substantial overhead. Instead of multi-table inheritance,

use explicit OneToOneFields and ForeignKeys between models so you can control

when joins are traversed. In our combined 20+ years of doing Django we’ve never seen

multi-table inheritance cause anything but trouble.

6.1.3 Model Inheritance in Practice: The TimeStampedModel

It’s very common in Django projects to include a created and modified timestamp

field on all your models. We could manually add those fields to each and every model,

but that’s a lot of work and adds the risk of human error. A better solution is to write a

TimeStampedModel to do the work for us:

Example 6.1: core/models.py

from django.db import models

class TimeStampedModel(models.Model):

"""

An abstract base class model that provides self-

updating ``created`` and ``modified`` fields.

"""

created = models.DateTimeField(auto_now_add=True)

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

65

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 11322Chapter 6: Model Best Practices

modified = models.DateTimeField(auto_now=True)

class Meta:

abstract = True

Take careful note of the very last two lines in the example, which turn our example into an
abstract base class:

Example 6.2: Defining an abstract base class

class Meta:

abstract = True

By defining TimeStampedModel as an abstract base class when we define a new class that

inherits from it, Django doesn’t create a core_timestampedmodel table when migrate

is run.

Let’s put it to the test:

Example 6.3: flavors/models.py

# flavors/models.py

from django.db import models

from core.models import TimeStampedModel

class Flavor(TimeStampedModel):

title = models.CharField(max_length=200)

This only creates one table: the flavors_flavor database table. That’s exactly the behavior

we wanted.

On the other hand, if TimeStampedModel was not an abstract base class (i.e. a concrete

base class via multi-table inheritance), it would also create a core_timestampedmodel

table. Not only that, but all of its subclasses including Flavor would lack the fields and

have implicit foreign keys back to TimeStampedModel just to handle created/modified

timestamps. Any reference to Flavor that reads or writes to the TimeStampedModel

would impact two tables. (Thank goodness it’s abstract!)

66

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 113226.2: Database Migrations

Remember, concrete inheritance has the potential to become a nasty performance bottle-

neck. This is even more true when you subclass a concrete model class multiple times.

Further reading:

(cid:228) docs.djangoproject.com/en/3.2/topics/db/models/

#model-inheritance

6.2 Database Migrations
Django comes with a powerful database change propagation library aptly called

“migrations”, or as we prefer to refer to it in the book, django.db.migrations.

6.2.1 Tips for Creating Migrations

(cid:228) As soon as a new app or model is created, take that extra minute to create the

initial django.db.migrations for that new model. All we do is type python

manage.py makemigrations.

(cid:228) Examine the generated migration code before you run it, especially when complex

changes are involved. Also, review the SQL that will be used with the sqlmigrate

command.

(cid:228) Use the MIGRATION_MODULES setting to manage writing migrations for third-party

apps that don’t have their own django.db.migrations-style migrations.

(cid:228) Don’t worry about how many migrations are created. If the number of migrations

becomes unwieldy, use squashmigrations to bring them to heel.

(cid:228) Always back up your data before running a migration.

6.2.2 Adding Python Functions and Custom SQL to Migrations

django.db.migrations can’t anticipate complex changes to your data, or to external

components that interact with your data. That’s when it’s useful to delve into writing python

or custom SQL to aid in running migrations. At some point in any project that hits produc-

tion, you’ll find a reason to use either the RunPython or RunSQL classes:

(cid:228) docs.djangoproject.com/en/3.2/ref/migration-operations/

#runpython

(cid:228) docs.djangoproject.com/en/3.2/ref/migration-operations/#runsql

For what it’s worth, our preference is to use RunPython before RunSQL, but we advise

sticking to where your strengths are.

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

67

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 11322Chapter 6: Model Best Practices

6.3 Overcoming Common Obstacles of RunPython
When we write RunPython-called functions, we encounter a few pain points. Most, but

not all of these can be resolved.

6.3.1 Getting Access to a Custom Model Manager’s Methods

Sometimes you want to be able to filter, exclude, create, or modify records by us-

ing custom model manager methods. However, by default django.db.migrations

excludes these components. Fortunately, we can override this behavior by adding a
use_in_migrations = True flag to our custom managers.

See: docs.djangoproject.com/en/3.2/topics/migrations/#model-managers

6.3.2 Getting Access to a Custom Model Method

Due to how django.db.migrations serializes models, there’s no way around this limi-

tation. You simply cannot call any custom methods during a migration. See the reference

link below:

docs.djangoproject.com/en/3.2/topics/migrations/#historical-models

WARNING: Watch Out for Custom Save and Delete Methods

If you override a model’s save and delete methods, they won’t be called when called

by RunPython. Consider yourself warned, this can be a devastating gotcha.

6.3.3 Use RunPython.noop to Do Nothing

In order for reverse migrations to work, RunPython must be given a reverse_code callable
to undo the effects of the code callable. However, some of the code callables that we write

are idempotent. For example, they combine existing data into a newly added field. Writing
a reverse_code callable for these functions is either impossible or pointless. When this
happens, use RunPython.noop as the reverse_code .

For example, let’s say we create a new model called “Cone”. All existing scoops need
their own cone, so we write an add_cones function to add the cones to the database.
However, when reversing the migration, writing code to remove the cones is pointless;
migrations.CreateModel.database_backwards will delete the cone.cone table and all
its records for us. Therefore, we should use RunPython.noop for the reverse_code :

68

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 113226.3: Overcoming Common Obstacles of RunPython

Example 6.4: RunPython Reversal with RunPython.noop

from django.db import migrations, models

def add_cones(apps, schema_editor):

Scoop = apps.get_model('scoop', 'Scoop')

Cone = apps.get_model('cone', 'Cone')

for scoop in Scoop.objects.all():

Cone.objects.create(

scoop=scoop,

style='sugar'

)

class Migration(migrations.Migration):

initial = True

dependencies = [

('scoop', '0051_auto_20670724'),

]

operations = [

migrations.CreateModel(

name='Cone',

fields=[

('id', models.AutoField(auto_created=True,

,→

primary_key=True,

serialize=False, verbose_name='ID')),

('style', models.CharField(max_length=10),

choices=[('sugar', 'Sugar'), ('waffle',

,→

'Waffle')]),

('scoop', models.OneToOneField(null=True,

,→

to='scoop.Scoop'

on_delete=django.db.models.deletion.SET_NULL,

,→

)),

],

),

# RunPython.noop does nothing but allows reverse migrations

,→

to occur

migrations.RunPython(add_cones, migrations.RunPython.noop)

]

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

69

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 11322Chapter 6: Model Best Practices

6.3.4 Deployment and Management of Migrations

(cid:228) It goes without saying, but we’ll say it anyway: Always back up your data before run-

ning a migration.

(cid:228) Before deployment, check that you can rollback migrations! We can’t always have

perfect round-trips, but not being able to roll back to an earlier state really hurts bug

tracking and sometimes deployment in larger projects.

(cid:228) If a project has tables with millions of rows in them, do extensive tests against data

of that size on staging servers before running a migration on a production server.

Migrations on real data can take much, much, much more time than anticipated.

(cid:228) If you are using MySQL:

(cid:228) You absolutely positively must back up the database before any schema change.

MySQL lacks transaction support around schema changes, hence rollbacks are

impossible.

(cid:228) If you can, put the project in read-only mode before executing the change.

(cid:228) If not careful, schema changes on heavily populated tables can take a long time.

Not seconds or minutes, but hours.

Figure 6.1: Cones migrating south for the winter. Django’s built-in migration system started
out as an external project called South.

TIP: Always Put Data Migration Code Into Source Control

Including migration code in VCS is an absolute necessity. Not including migration

code in version control is just like not including settings files in VCS: You might

be able to develop, but should you switch machines or bring someone else into the
project, then everything will break.

6.4 Django Model Design
One of the most difficult topics that receive the least amount of attention is how to design

good Django models.

70

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 11322How do you design for performance without optimizing prematurely? Let’s explore some

6.4: Django Model Design

strategies here.

6.4.1

Start Normalized

We suggest that readers of this book need to be familiar with database normalization. If
you are unfamiliar with database normalization, make it your responsibility to gain an un-

derstanding, as working with models in Django effectively requires a working knowledge

of this. Since a detailed explanation of the subject is outside the scope of this book, we

recommend the following resources:

(cid:228) en.wikipedia.org/wiki/Database_normalization

(cid:228) en.wikibooks.org/wiki/Relational_Database_Design/Normalization

When you’re designing your Django models, always start off normalized. Take the time to

make sure that no model should contain data already stored in another model.

At this stage, use relationship fields liberally. Don’t denormalize prematurely. You want to

have a good sense of the shape of your data.

6.4.2 Cache Before Denormalizing

Often, setting up caching in the right places can save you the trouble of denormalizing your

models. We’ll cover caching in much more detail in Chapter 26: Finding and Reducing

Bottlenecks, so don’t worry too much about this right now.

6.4.3 Denormalize Only if Absolutely Needed

It can be tempting, especially for those new to the concepts of data normalization, to denor-

malize prematurely. Don’t do it! Denormalization may seem like a panacea for what causes

problems in a project. However, it’s a tricky process that risks adding complexity to your

project and dramatically raises the risk of losing data.

Please, please, please explore caching before denormalization.

When a project has reached the limits of what the techniques described in Chapter 26:

Finding and Reducing Bottlenecks can address, that’s when research into the concepts and

patterns of database denormalization should begin.

6.4.4 When to Use Null and Blank

When defining a model field, you have the ability to set the null=True and the

blank=True options. By default, they are False.

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

71

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 11322Chapter 6: Model Best Practices

Knowing when to use these options is a common source of confusion for developers.

We’ve put table Table 6.2: When to Use Null and Blank by Field together to serve as a guide

for standard usage of these model field arguments.

Figure 6.2: A common source of confusion.

6.4.5 When to Use BinaryField

This field allows for the storage of raw binary data or bytes. We can’t perform filters, excludes,

or other SQL actions on the field, but there are use cases for it. For example, we could store:

(cid:228) MessagePack-formatted content.

(cid:228) Raw sensor data.

(cid:228) Compressed data e.g. the type of data Sentry stores as a BLOB, but is required to

base64-encode due to legacy issues.

The possibilities are endless, but remember that binary data can come in huge chunks, which

can slow down databases. If this occurs and becomes a bottleneck, the solution might be to

save the binary data in a file and reference it with a FileField.

WARNING: Don’t Serve Files From BinaryField!

Storing files in a database field should never happen. If it’s being considered as a

solution to a problem, find a certified database expert and ask for a second opinion.

To summarize PostgreSQL expert Frank Wiles on the problems with using a

database as a file store:

(cid:228) ‘read/write to a DB is always slower than a filesystem’

72

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 113226.4: Django Model Design

Field Type
CharField,
TextField,
SlugField,
EmailField,
CommaSeparated-
IntegerField,
UUIDField

FileField,
ImageField

BooleanField
IntegerField,
FloatField,
DecimalField,
DurationField, etc

Setting null=True
Okay if you also have set
both unique=True and
blank=True. In this sit-
uation, null=True is re-
quired to avoid unique con-
straint violations when sav-
ing multiple objects with
blank values.

Don’t do this.
Django stores
the path
from MEDIA_ROOT to the
file or to the image in a
CharField, so the same pat-
tern applies to FileFields.
Okay.
Okay if you want to be able
to set the value to NULL in
the database.

DateTimeField,
DateField,
TimeField, etc.

Okay if you want to be able
to set the value to NULL in
the database.

ForeignKey,
OneToOneField

Okay if you want to be able
to set the value to NULL in
the database.

ManyToManyField

Null has no effect

GenericIPAddressField Okay if you want to be able
to set the value to NULL in
the database.

JSONField

Okay.

Setting blank=True
Okay if you want the cor-
responding form widget
to accept empty values. If
you set this, empty values
are stored as NULL in the
database
if null=True
and unique=True are also
set. Otherwise,
they get
stored as empty strings.
Okay.
The
CharField applies here.

pattern

same

for

Default is blank=True.
Okay if you want the cor-
responding form widget to
accept empty values. If so,
you will also want to set
null=True.
Okay if you want the cor-
responding form widget to
accept empty values, or if
you are using auto_now or
auto_now_add. If it’s the
former, you will also want
to set null=True.
Okay if you want the cor-
responding form widget
(e.g.
to
the select box)
accept empty values. If so,
you will also want to set
null=True.
Okay if you want the corre-
sponding form widget (e.g.
the select box) to accept
empty values.
Okay if you want to make
the
corresponding field
widget accept empty values.
If so, you will also want to
set null=True.
Okay.

Table 6.2: When to Use Null and Blank by Field

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

73

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 11322Chapter 6: Model Best Practices

(cid:228) ‘your DB backups grow to be huge and more time consuming’

(cid:228) ‘access to the files now requires going through your app (Django) and DB

layers’

See revsys.com/blog/2012/may/01/three-things-you-should-never-put-

your-database/

When someone thinks there is a good use case for serving files from a database and

quotes a success like npmjs.org (stored files in CouchDB), it’s time to do your

research. The truth is that npmjs.org, migrated its database-as-file-store system

to a more traditional file serving method years ago.

6.4.6 Try to Avoid Using Generic Relations

In

general

we

advocate

against

generic

relations

and

use

of

models.field.GenericForeignKey. They are usually more trouble than they are

worth. Using them is often a sign that troublesome shortcuts are being taken, that the

wrong solution is being explored.

The idea of generic relations is that we are binding one table to another by way of an uncon-

strained foreign key (GenericForeignKey). Using it is akin to using a NoSQL datastore

that lacks foreign key constraints as the basis for projects that could really use foreign key

constraints. This causes the following:

(cid:228) Reduction in speed of queries due to lack of indexing between models.

(cid:228) Danger of data corruption as a table can refer to another against a non-existent record.

The upside of this lack of constraints is that generic relations make it easier to build apps for

things that need to interact with numerous model types we might have created. Specifically
things like favorites, ratings, voting, messages, and tagging apps. Indeed, there are a number

of existing apps that are built this way. While we hesitate to use them, we are comforted by

the fact that the good ones are focused on a single task (for example, tagging).

Over time, we’ve found that we can build favorites, ratings, voting, messages, and tagging

apps built off ForeignKey and ManyToMany field. For a little more development work, by

avoiding the use of GenericForeignKey we get the benefit of speed and integrity.

Where the GenericForeignKey becomes really troublesome is when its unconstrained

feature becomes the method by which a project’s primary data is defined. For example, if

we built an Ice Cream themed project where the relationships between toppings, flavors,

74

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 113226.4: Django Model Design

containers, orders, and sales were all tracked via GenericForeignKey, we would have the

problems described in the bullets above. In short:

(cid:228) Try to avoid generic relations and GenericForeignKey.

(cid:228) If you think you need generic relations, see if the problem can be solved through better

model design or the new PostgreSQL fields.

(cid:228) If usage can’t be avoided, try to use an existing third-party app. The isolation a third-

party app provides will help keep data cleaner.

For another view that shares our opinion, please read lukeplant.me.uk/blog/posts/

avoid-django-genericforeignkey

6.4.7 Make Choices and Sub-Choices Model Constants

A nice pattern is to add choices as properties to a model as a structure defined with tuples.

As these are constants tied to your model (and the represented data) being able to easily

access them everywhere makes development easier.

This technique is described in docs.djangoproject.com/en/3.2/ref/models/

fields/#django.db.models.Field.choices. If we translate that to an ice cream-

based example, we get:

Example 6.5: Setting Choice Model Attributes

# orders/models.py

from django.db import models

class IceCreamOrder(models.Model):

FLAVOR_CHOCOLATE = 'ch'

FLAVOR_VANILLA = 'vn'

FLAVOR_STRAWBERRY = 'st'

FLAVOR_CHUNKY_MUNKY = 'cm'

FLAVOR_CHOICES = (

(FLAVOR_CHOCOLATE, 'Chocolate'),

(FLAVOR_VANILLA, 'Vanilla'),

(FLAVOR_STRAWBERRY, 'Strawberry'),

(FLAVOR_CHUNKY_MUNKY, 'Chunky Munky')

)

flavor = models.CharField(

max_length=2,

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

75

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 11322Chapter 6: Model Best Practices

choices=FLAVOR_CHOICES

)

Using this model, we can do the following:

Example 6.6: Accessing Choice Model Attributes

>>> from orders.models import IceCreamOrder

>>>

,→

IceCreamOrder.objects.filter(flavor=IceCreamOrder.FLAVOR_CHOCOLATE)

[<icecreamorder: 35>, <icecreamorder: 42>, <icecreamorder: 49>]

This works in both Python code and templates, and the attribute can be accessed on either

the class or the instantiated model object.

6.4.8 Using Enumeration Types for Choices

Nate Cox recommends using Django’s enumeration types for choices. Built into Django as

of the release of 3.0, it’s even easier to use.

Example 6.7: Setting Choice Model Attributes

from django.db import models

class IceCreamOrder(models.Model):

class Flavors(models.TextChoices):

CHOCOLATE = 'ch', 'Chocolate'

VANILLA = 'vn', 'Vanilla'

STRAWBERRY = 'st', 'Strawberry'

CHUNKY_MUNKY = 'cm', 'Chunky Munky'

flavor = models.CharField(

max_length=2,

choices=Flavors.choices

)

Using this code we’re able to do:

76

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 113226.5: The Model _meta API

Example 6.8: Accessing Enum-Based Choice Model Attributes

>>> from orders.models import IceCreamOrder

>>>

,→

IceCreamOrder.objects.filter(flavor=IceCreamOrder.Flavors.CHOCOLATE)

[<icecreamorder: 35>, <icecreamorder: 42>, <icecreamorder: 49>]

There are a few drawbacks to using enumeration types over the previous method. Specifi-

cally:

(cid:228) Named groups are not possible with enumeration types. What this means is that if

we want to have categories inside our choices, we’ll have to use the older tuple-based

approach.

(cid:228) If we want other types besides str and int, we have to define those ourselves.

Enumeration types for choice fields provide a lovely API. We’ve found an excellent approach

to using them is to stick with them until we run into the drawbacks listed above. Then we

switch to the older tuple-based method.

6.4.9 PostgreSQL-Specific Fields: When to Use Null and Blank

Field Type
ArrayField
HStoreField
IntegerRangeField,
BigIntegerRangeField,
and FloatRangeField

Setting null=True
Okay.
Okay.
Okay if you want to be able
to set the value to NULL in
the database.

DatetimeRangeField
and DateRangeField

Okay if you want to be able
to set the value to NULL in
the database.

Setting blank=True
Okay.
Okay.
Okay if you want the cor-
responding form widget to
accept empty values. If so,
you will also want to set
null=True.
Okay if you want the cor-
responding form widget to
accept empty values, or if
you are using auto_now
or auto_now_add. If
so,
you will also want to set
null=True.

Table 6.3: When to Use Null and Blank for Postgres Fields

6.5 The Model _meta API
This _meta API is unusual in the following respects:

(cid:228) It is prefixed with “_” yet is a public, documented API.

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

77

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 11322Chapter 6: Model Best Practices

(cid:228) Unlike other _-prefixed components of Django _meta follows the same deprecation

patterns as the rest of the framework.

The reason for this is that before Django 1.8, the model _meta API was unofficial and

purposely undocumented, as is normal with any API subject to change without notice. The

original purpose of _meta was simply for Django to store extra info about models for its

own use. However, it proved so useful that it is now a documented API.

For most projects, you shouldn’t need _meta. The main uses for it are when you need to:

(cid:228) Get a list of a model’s fields.

(cid:228) Get the class of a particular field for a model (or its inheritance chain or other info

derived from such).

(cid:228) Ensure that how you get this information remains constant across future Django ver-

sions.

Examples of these sorts of situations:

(cid:228) Building a Django model introspection tool.

(cid:228) Building your own custom specialized Django form library.

(cid:228) Creating admin-like tools to edit or interact with Django model data.

(cid:228) Writing visualization or analysis libraries, e.g. analyzing info only about fields that

start with “foo”.

Further reading:

(cid:228) Model _meta docs: docs.djangoproject.com/en/3.2/ref/models/meta/

6.6 Model Managers
Every time we use the Django ORM to query a model, we are using an interface called a

model manager to interact with the database. Model managers are said to act on the full

set of all possible instances of this model class (all the data in the table) to restrict the ones

you want to work with. Django provides a default model manager for each model class, but

we can define our own.

Here’s a simple example of a custom model manager:

Example 6.9: Custom Model Manager: published

from django.db import models

from django.utils import timezone

78

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 113226.6: Model Managers

class PublishedManager(models.Manager):

def published(self, **kwargs):

return self.filter(pub_date__lte=timezone.now(), **kwargs)

class FlavorReview(models.Model):

review = models.CharField(max_length=255)

pub_date = models.DateTimeField()

# add our custom model manager

objects = PublishedManager()

Now, if we first want to display a count of all of the ice cream flavor reviews, and then a

count of just the published ones, we can do the following:

Example 6.10: Custom Model Manager: published

>>> from reviews.models import FlavorReview

>>> FlavorReview.objects.count()

35

>>> FlavorReview.objects.published().count()

31

Easy, right? Yet wouldn’t it make more sense if you just added a second model manager?

That way you could have something like:

Example 6.11: Illusory Benefits of Using Two Model Managers

>>> from reviews.models import FlavorReview

>>> FlavorReview.objects.filter().count()

35

>>> FlavorReview.published.filter().count()

31

On the surface, replacing the default model manager seems like the intelligent thing to do.

Unfortunately, our experiences in real project development make us very careful when we

use this method. Why?

First, when using model inheritance, children of abstract base classes receive their parent’s

model manager, and children of concrete base classes do not.

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

79

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 11322Chapter 6: Model Best Practices

Second, the first manager applied to a model class is the one that Django treats as the

default. This breaks significantly with the normal Python pattern, causing what can

appear to be unpredictable results from QuerySets.

With this knowledge in mind, in your model class, objects = models.Manager()

should be defined manually above any custom model manager.

WARNING: Know the Model Manager Order of Operations

Always set objects = models.Manager() above any custom model manager

that has a new name. While this rule can be broken, it’s an advanced technique that

we don’t recommend for most projects.

Additional reading: docs.djangoproject.com/en/3.2/topics/db/managers/

6.7 Understanding Fat Models
The concept of fat models is that rather than putting data-related code in views and tem-

plates, instead, we encapsulate the logic in model methods, classmethods, properties, even

manager methods. That way, any view or task can use the same logic. For example, if we have

a model that represents Ice Cream reviews we might attach to it the following methods:

(cid:228) Review.create_review(cls, user, rating, title, description) A

classmethod for creating reviews. Called on the model class itself from HTML

and REST views, as well as an import tool that accepts spreadsheets.

(cid:228) Review.product_average A review instance property that returns the reviewed

product’s average rating. Used on review detail views so the reader can get a feel for

the overall opinion without leaving the page.

(cid:228) Review.found_useful(self, user, yes) A method that sets whether or not

readers found the review useful or not. Used in detail and list views, for both HTML

and REST implementations.

As can be inferred from this list, fat models are a great way to improve the reuse of code

across a project. In fact, the practice of moving logic from views and templates to models

has been growing across projects, frameworks, and languages for years. This is a good thing,

right?

Not necessarily.

The problem with putting all logic into models is it can cause models to explode in size of

code, becoming what is called a ‘god object’. This anti-pattern results in model classes that

80

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 113226.8: Additional Resources

are hundreds, thousands, even tens of thousands of lines of code. Because of their size and

complexity, god objects are hard to understand, hence hard to test and maintain.

When moving logic into models, we try to remember one of the basic ideas of object-

oriented programming, that big problems are easier to resolve when broken up into smaller

problems. If a model starts to become unwieldy in size, we begin isolating code that is

prime for reuse across other models, or whose complexity requires better management. The

methods, classmethods, and properties are kept, but the logic they contain is moved into

Model Behaviors or Stateless Helper Functions. Let’s cover both techniques in the following

subsections:

6.7.1 Model Behaviors a.k.a Mixins

Model behaviors embrace the idea of composition and encapsulation via the use of mix-

ins. Models inherit logic from abstract models. For more information, see the following

resources:

(cid:228) blog.kevinastone.com/django-model-behaviors.html Kevin Stone’s arti-

cle on using composition to reduce replication of code.

(cid:228) Section 10.2: Using Mixins With CBVs.

6.7.2

Stateless Helper Functions

By moving logic out of models and into utility functions, it becomes more isolated. This

isolation makes it easier to write tests for the logic. The downside is that the functions are
stateless, hence all arguments have to be passed.

We cover this in Chapter 31: What About Those Random Utilities?

6.7.3 Model Behaviors vs Helper Functions

In our opinion, alone neither of these techniques is perfect. However, when both are used

judiciously, they can make projects shine. Understanding when to use either isn’t a static

science, it is an evolving process. This kind of evolution is tricky, prompting our suggestion

to have tests for the components of fat models.

6.8 Additional Resources
Here are a number of articles that build on what we illustrate in this chapter:

(cid:228) hakibenita.com/bullet-proofing-django-models - Haki Benita’s excellent

article on implementing very serious rules to Django models. His entire blog is full

of excellent information.

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

81

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 11322Chapter 6: Model Best Practices

(cid:228) - Andrew Brooks’ deep dive into Django’s ORM is worth the read for anyone

concerned about the performance of their model design. spellbookpress.com/

books/temple-of-django-database-performance/

6.9 Summary
Models are the foundation for most Django projects, so take the time to design them

thoughtfully.

Start normalized, and only denormalize if you’ve already explored other options thoroughly.

You may be able to simplify slow, complex queries by dropping down to raw SQL, or you

may be able to address your performance issues with caching in the right places.

If you decide to use model inheritance, inherit from abstract base classes rather than concrete

models. You’ll save yourself from the confusion of dealing with implicit, unneeded joins.

Watch out for the “gotchas” when using the null=True and blank=True model field

options. Refer to our handy table for guidance.

You may find django-model-utils and django-extensions pretty handy.

Finally, fat models are a way to encapsulate logic in models, but can all too readily turn into

god objects.

Our next chapter is where we begin talking about queries and the database layer.

82

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 113227 | Queries and the Database Layer

Most of the queries we write are simple. Django’s Object-Relational Model or ORM pro-

vides a great productivity shortcut: not only generating decent SQL queries for common use

cases, but providing model access/update functionality that comes complete with validation

and security. It allows us to trivially write code that works with different database engines.

This feature of ORMs powers much of the Django third-party package ecosystem. If you

can write your query easily with the ORM, then take advantage of it!

The Django ORM, like any ORM, converts data from different types into objects that we

can use pretty consistently across supported databases. Then it provides a set of methods for

interacting with those objects. For the most part, Django does a pretty good job at what

it’s designed to do. However, it does have quirks, and understanding those quirks is part of

learning how to use Django. Let’s go over some of them, shall we?

7.1 Use get_object_or_404() for Single Objects
In views such as detail pages where you want to retrieve a single object and do something

with it, use get_object_or_404() instead of get().

WARNING: get_object_or_404() Is for Views Only

(cid:228) Only use it in views.

(cid:228) Don’t use it in helper functions, forms, model methods or anything that is

not a view or directly view related.

Many years ago a certain Python coder and author named Daniel was deploying

his first Django project. So entranced was he by Django’s get_object_or_404()

function that he used it everywhere, in views, in models, in forms, everywhere. In

development this worked great and passed tests. Unfortunately, this unconstrained
use meant that when certain records were deleted by the admin staff, the entire site

broke.

Keep get_object_or_404() in your views!

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

83

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 11322Chapter 7: Queries and the Database Layer

7.2 Be Careful With Queries That Might Throw

Exceptions

When you’re getting a single Django model instance with the get_object_or_404()

you don’t need to wrap it

shortcut,
in a
get_object_or_404() already does that for you.

try-except block. That’s because

However, in most other situations you need to use a try-except block. Some tips:

7.2.1 ObjectDoesNotExist vs. DoesNotExist

ObjectDoesNotExist can be applied to any model object, whereas DoesNotExist is for

a specific model.

Example 7.1: Example Use for ObjectDoesNotExist

from django.core.exceptions import ObjectDoesNotExist

from flavors.models import Flavor

from store.exceptions import OutOfStock

def list_flavor_line_item(sku):

try:

return Flavor.objects.get(sku=sku, quantity__gt=0)

except Flavor.DoesNotExist:

msg = 'We are out of {0}'.format(sku)

raise OutOfStock(msg)

def list_any_line_item(model, sku):

try:

return model.objects.get(sku=sku, quantity__gt=0)

except ObjectDoesNotExist:

msg = 'We are out of {0}'.format(sku)

raise OutOfStock(msg)

7.2.2 When You Just Want One Object but Get Three Back

If

it’s possible that your query may return more than one object, check for a

MultipleObjectsReturned exception. Then in the except clause, you can do whatever

makes sense, e.g. raise a special exception or log the error.

84

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 113227.3: Use Lazy Evaluation to Make Queries Legible

Example 7.2: Example Use of MultipleObjectsReturned

from flavors.models import Flavor

from store.exceptions import OutOfStock, CorruptedDatabase

def list_flavor_line_item(sku):

try:

return Flavor.objects.get(sku=sku, quantity__gt=0)

except Flavor.DoesNotExist:

msg = 'We are out of {}'.format(sku)

raise OutOfStock(msg)

except Flavor.MultipleObjectsReturned:

msg = 'Multiple items have SKU {}. Please fix!'.format(sku)

raise CorruptedDatabase(msg)

7.3 Use Lazy Evaluation to Make Queries Legible
Django’s ORM is very powerful. And with such power comes the responsibility to make

code legible, hence maintainable. With complex queries, attempt to avoid chaining too

much functionality on a small set of lines:

Example 7.3: Illegible Queries

# Don't do this!

from django.db.models import Q

from promos.models import Promo

def fun_function(name=None):

"""Find working ice cream promo"""

,→

# Too much query chaining makes code go off the screen or page. Not good.

return

,→

Promo.objects.active().filter(Q(name__startswith=name)|Q(description__icontains=name)).exclude(status='melted')

This is unpleasant, right? Yet if we add in advanced Django ORM tools, then it will go

from unpleasant to as terrible as a sriracha-based ice cream topping. To mitigate this un-

pleasantness, we can use the lazy evaluation feature of Django queries to keep our ORM

code clean.

By lazy evaluation, we mean that the Django ORM doesn’t make the SQL calls until the

data is actually needed. We can chain ORM methods and functions as much as we want,

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

85

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 11322Chapter 7: Queries and the Database Layer

and until we try to loop through the result, Django doesn’t touch the database. Instead of

being forced to chain many methods and advanced database features on a single line, we

can break them up over as many lines as needed. This increases readability, which improves

the ease of maintenance, which increases time for getting ice cream.

Here we take the code from bad example 7.3 and break it up into more legible code:

Example 7.4: Legible Queries

# Do this!

from django.db.models import Q

from promos.models import Promo

def fun_function(name=None):

"""Find working ice cream promo"""

results = Promo.objects.active()

results = results.filter(

Q(name__startswith=name) |

Q(description__icontains=name)

)

results = results.exclude(status='melted')

results = results.select_related('flavors')

return results

As can be seen in the corrected code, we can more easily tell what the end result will be.
Even better, by breaking up the query statement we can comment on specific lines of code.

7.3.1 Chaining Queries for Legibility

This technique borrows from the Pandas and JavaScript communities. Instead of using lazy

evaluation, it’s possible to chain queries thus:

Example 7.5: Chaining Queries

# Do this!

from django.db.models import Q

from promos.models import Promo

def fun_function(name=None):

"""Find working ice cream promo"""

86

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 113227.4: Lean on Advanced Query Tools

qs = (Promo

.objects

.active()

.filter(

Q(name__startswith=name) |

Q(description__icontains=name)

)

.exclude(status='melted')

.select_related('flavors')

)

return qs

The downside to this approach is that debugging isn’t as easy as using the lazy evaluation

method of writing a query. We simply can’t stick a PDB or IPDB call in the middle of a

query defined this way.

To get around this, we have to do a bit of commenting out:

Example 7.6: Debugging with Chained Queries

def fun_function(name=None):

"""Find working ice cream promo"""

qs = (

Promo

.objects

.active()

# .filter(

Q(name__startswith=name) |

Q(description__icontains=name)

#

#

# )

# .exclude(status='melted')

# .select_related('flavors')

)

breakpoint()

return qs

7.4 Lean on Advanced Query Tools
Django’s ORM is easy to learn, intuitive, and covers many use cases. Yet there are a number

of things it does not do well. What happens then is that, after the queryset is returned, we

begin processing more and more data in Python. This is a shame, because every database

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

87

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 11322Chapter 7: Queries and the Database Layer

manages and transforms data faster than Python (or Ruby, JavaScript, Go, Java, et al).

Instead of managing data with Python, we always try to use Django’s advanced query tools
to do the lifting. In doing so we not only benefit from increased performance, we also enjoy

using code that is more proven (Django and most databases are constantly tested) than any

Python-based workarounds we create.

7.4.1 Query Expressions

When performing reads on a database, query expressions can be used to create values or

computations during that read. If that sounds confusing, don’t feel alone, we’re confused

too. Since a code example is worth a thousand words, let’s provide an example of how they

can benefit us. In our case, we’re trying to list all the customers who have on average ordered

more than one scoop per visit to an ice cream store.

First, how this might be done, albeit dangerously, without query expressions:

Example 7.7: No Query Expressions

# Don't do this!

from models.customers import Customer

customers = []

for customer in Customer.objects.iterator():

if customer.scoops_ordered > customer.store_visits:

customers.append(customer)

This example makes us shudder with fear. Why?

(cid:228) It uses Python to loop through all the Customer records in the database, one by one.

This is slow and memory consuming.

(cid:228) Under any volume of use, it will generate race conditions. This occurs when we’re

running the script while customers interact with the data. While probably not an

issue in this simple ‘READ’ example, in real-world code combining that with an

‘UPDATE’ can lead to loss of data.

Fortunately, through query expressions Django provides a way to make this more efficient

and race-condition free:

88

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 113227.4: Lean on Advanced Query Tools

Example 7.8: Yes Query Expressions

from django.db.models import F

from models.customers import Customer

customers =

,→

Customer.objects.filter(scoops_ordered__gt=F('store_visits'))

What this does is use the database itself to perform the comparison. Under the hood, Django

is running something that probably looks like:

Example 7.9: Query Expression Rendered as SQL

SELECT * from customers_customer where scoops_ordered >

,→

store_visits

Query Expressions should be in your toolkit. They increase the performance and stability

of projects.

(cid:228) docs.djangoproject.com/en/3.2/ref/models/expressions/

7.4.2 Database Functions

Since Django 1.8 we’ve been able to easily use common database functions such

as UPPER(), LOWER(), COALESCE(), CONCAT(), LENGTH(), and SUBSTR(). Of

all the advanced query tools provided by Django, these are our favorites. Why?

1 Very easy to use, either on new projects or existing projects.

2 Database functions allow us to move some of the logic from Python to the database.

This can be a performance booster, as processing data in Python is not as fast as

processing data in a database.

3 Database functions are implemented differently per database, but Django’s ORM

abstracts this away. Code we write using them on PostgreSQL will work on MySQL

or SQLite3.

4 They are also query expressions, which means they follow a common pattern already

established by another nice part of the Django ORM.

Reference:

(cid:228) docs.djangoproject.com/en/3.2/ref/models/database-functions/

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

89

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 11322Chapter 7: Queries and the Database Layer

7.5 Don’t Drop Down to Raw SQL Until It’s Necessary
Whenever we write raw SQL we lose elements of security and reusability. This doesn’t just

apply to internal project code, but also to the rest of the Django world. Specifically, if you

ever release one of your Django apps as a third-party package, using raw SQL will decrease
the portability of the work. Also, in the rare event that the data has to be migrated from one

database to another, any database-specific features that you use in your SQL queries will

complicate the migration.

So when should you actually write raw SQL? If expressing your query as raw SQL would

drastically simplify your Python code or the SQL generated by the ORM, then go ahead

and do it. For example, if you’re chaining a number of QuerySet operations that each operate

on a large data set, there may be a more efficient way to write it as raw SQL.

TIP: Malcolm Tredinnick’s Advice on Writing SQL in Django

Django core developer Malcolm Tredinnick said (paraphrased):

“The ORM can do many wonderful things, but sometimes SQL is the

right answer. The rough policy for the Django ORM is that it’s a storage

layer that happens to use SQL to implement functionality. If you need

to write advanced SQL you should write it. I would balance that by

cautioning against overuse of the raw() and extra() methods.”

TIP: Jacob Kaplan-Moss’ Advice on Writing SQL in Django

Django project co-leader Jacob Kaplan-Moss says (paraphrased):

“If it’s easier to write a query using SQL than Django, then do it.

extra() is nasty and should be avoided; raw() is great and should

be used where appropriate.”

90

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 113227.6: Add Indexes as Needed

Figure 7.1: This flavor of ice cream contains raw SQL. It’s a bit chewy.

7.6 Add Indexes as Needed
While adding db_index=True to any model field is easy, understanding when it should

be done takes a bit of judgment. Our preference is to start without indexes and add them

as needed.

When to consider adding indexes:

(cid:228) The index would be used frequently, as in 10–25% of all queries.

(cid:228) There is real data, or something that approximates real data, so we can analyze the

results of indexing.

(cid:228) We can run tests to determine if indexing generates an improvement in results.

When using PostgreSQL, pg_stat_activity tells us what indexes are actually being

used.

Once a project goes live, Chapter 26: Finding and Reducing Bottlenecks, has information

on index analysis.

TIP: Class-Based Model Indexes

Django provides the django.db.models.indexes module, the Index class,

and the Meta.indexes option. These make it easy to create all sorts of

database indexes:

just subclass Index, add it to Meta.indexes, and you’re

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

91

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 11322Chapter 7: Queries and the Database Layer

done! django.contrib.postgres.indexes currently includes BrinIndex

and GinIndex, but you can imagine HashIndex, GistIndex, SpGistIndex, and

more.

(cid:228) docs.djangoproject.com/en/3.2/ref/models/indexes/

(cid:228) docs.djangoproject.com/en/3.2/ref/models/options/

#indexes

7.7 Transactions
The default behavior of the ORM is to autocommit every query when it is called. In the

case of data modification, this means that every time a .create() or .update() is called,

it immediately modifies data in the SQL database. The advantage of this is that it makes

it easier for beginning developers to understand the ORM. The disadvantage is that if a

view (or some other operation) requires two or more database modifications to occur, if one

modification succeeds and the other fails, the database is at risk of corruption.

The way to resolve the risk of database corruption is through the use of database transactions.

A database transaction is where two or more database updates are contained in a single unit

of work. If a single update fails, all the updates in the transaction are rolled back. To make

this work, a database transaction, by definition, must be atomic, consistent, isolated and
durable. Database practitioners often refer to these properties of database transactions using

the acronym ACID.

Django has a powerful and relatively easy-to-use transaction mechanism. This makes it

much easier to lock down database integrity on a project, using decorators and context

managers in a rather intuitive pattern.

7.7.1 Wrapping Each HTTP Request in a Transaction

Example 7.10: Wrapping Each HTTP Request in a Transaction

# settings/base.py

DATABASES = {

'default': {

# ...

'ATOMIC_REQUESTS': True,

},

}

Django makes it easy to handle all web requests inside of a transaction with the

92

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 113227.7: Transactions

ATOMIC_REQUESTS setting. By setting it to True as shown above, all requests are wrapped

in transactions, including those that only read data. The advantage of this approach is safety:

all database queries in views are protected, the disadvantage is performance can suffer. We

can’t tell you just how much this will affect performance, as it depends on individual database

design and how well various database engines handle locking.

We’ve found that this is a great way to ensure at the start that a write-heavy project’s database

maintains integrity. With lots of traffic, however, we’ve had to go back and change things

to a more focused approach. Depending on the size this can be a small or monumental task.

Another thing to remember when using ATOMIC_REQUESTS, is that only the database

state is rolled back on errors. It’s embarrassing to send out a confirmation email and then

have the transaction that wraps a request rolled back. This problem may crop up with any

“write” to anything other than the database: sending email or SMS, calling a third-party

API, writing to the filesystem, etc. Therefore, when writing views that create/update/delete

records but interact with non-database items, you may choose to decorate the view with

transaction.non_atomic_requests().

WARNING: Aymeric Augustin on non_atomic_requests()

Core Django developer and main implementer of the new transaction system,

Aymeric Augustin says, “This decorator requires tight coupling between views and

models, which will make a code base harder to maintain. We might have come up

with a better design if we hadn’t had to provide for backwards-compatibility.”

Then you can use the more explicit declaration as described below in this super-simple API-

style function-based view:

Example 7.11: Simple Non-Atomic View

# flavors/views.py

from django.db import transaction

from django.http import HttpResponse

from django.shortcuts import get_object_or_404

from django.utils import timezone

from .models import Flavor

@transaction.non_atomic_requests

def posting_flavor_status(request, pk, status):

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

93

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 11322Chapter 7: Queries and the Database Layer

flavor = get_object_or_404(Flavor, pk=pk)

# This will execute in autocommit mode (Django's default).

flavor.latest_status_change_attempt = timezone.now()

flavor.save()

with transaction.atomic():

# This code executes inside a transaction.

flavor.status = status

flavor.latest_status_change_success = timezone.now()

flavor.save()

return HttpResponse('Hooray')

# If the transaction fails, return the appropriate status

return HttpResponse('Sadness', status_code=400)

If you are using ATOMIC_REQUESTS=True and want to switch to a more focused approach

described in the following section, we recommend an understanding of Chapter 26: Find-

ing and Reducing Bottlenecks, Chapter 24: Testing Stinks and Is a Waste of Money!, and

Chapter 34: Continuous Integration before you undertake this effort.

TIP: Projects Touching Medical or Financial Data

For these kinds of projects, engineer systems for eventual consistency rather than

for transactional integrity. In other words, be prepared for transactions to fail and
rollbacks to occur. Fortunately, because of transactions, even with a rollback, the

data will remain accurate and clean.

7.7.2 Explicit Transaction Declaration

Explicit transaction declaration is one way to increase site performance. In other words,

specifying which views and business logic are wrapped in transactions and which are not.

The downside to this approach is that it increases development time.

TIP: Aymeric Augustin on ATOMIC_REQUESTS vs. Explicit
Transaction Declaration

Aymeric Augustin says, ‘Use ATOMIC_REQUESTS as long as the performance

overhead is bearable. That means “forever” on most sites.’

94

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 113227.7: Transactions

When it comes to transactions, here are some good guidelines to live by:

(cid:228) Database operations that do not modify the database should not be wrapped in trans-

actions.

(cid:228) Database operations that modify the database should be wrapped in a transaction.

(cid:228) Special cases including database modifications that require database reads and perfor-

mance considerations can affect the previous two guidelines.

If that’s not clear enough, here is a table explaining when different Django ORM calls

should be wrapped in transactions.

Purpose

Create Data

Retrieve Data

Modify Data
Delete Data

ORM method

.bulk_create(),

.create(),
.get_or_create(),
.get(), .filter(), .count(), .it-
erate(), .exists(), .exclude(),
.in_bulk, etc.
.update()
.delete()

Generally Use Transac-
tions?
3

3
3

Table 7.1: When to Use Transactions

Figure 7.2: Because no one loves ice cream quite like a database.

We also cover this in Chapter 26: Finding and Reducing Bottlenecks, specifically subsection

Section 26.2.4: Switch ATOMIC_REQUESTS to False.

TIP: Never Wrap Individual ORM Method Calls

Django’s ORM actually relies on transactions internally to ensure consistency of

data. For instance, if an update affects multiple tables because of concrete inheri-

tance, Django has that wrapped up in transactions.

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

95

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 11322Chapter 7: Queries and the Database Layer

Therefore, it is never useful to wrap an individual ORM method [.create(),

.update(), .delete()] call in a transaction. Instead, use explicit transactions

when you are calling several ORM methods in a view, function, or method.

7.7.3

django.http.StreamingHttpResponse and Transactions

If a view is returning django.http.StreamingHttpResponse, it’s impossible to handle

transaction errors once the response has begun. If your project uses this response method

then ATOMIC_REQUESTS should do one of the following:

1 Set ATOMIC_REQUESTS to Django’s default, which is False. Then you can use the

techniques explored in Section 7.7.2: Explicit Transaction Declaration. Or...

2 Wrap the view in the django.db.transaction.non_atomic_requests deco-

rator.

Keep in mind that you can use ATOMIC_REQUESTS with a streaming response, but the

transaction will only apply to the view itself. If the generation of the response stream triggers

additional SQL queries, they will be made in autocommit mode. Hopefully generating a

response doesn’t trigger database writes...

7.7.4 Transactions in MySQL

If the database being used is MySQL, transactions may not be supported depending on

your choice of table type such as InnoDB or MyISAM. If transactions are not supported,

Django will always function in autocommit mode, regardless of ATOMIC_REQUESTS or
code written to support transactions. For more information, we recommend reading the

following articles:

(cid:228) docs.djangoproject.com/en/3.2/topics/db/transactions/

#transactions-in-mysql

(cid:228) dev.mysql.com/doc/refman/8.0/en/sql-transactional-statements.

html

7.7.5 Django ORM Transaction Resources

(cid:228) docs.djangoproject.com/en/3.2/topics/db/transactions/ Django’s

documentation on transactions.

(cid:228) Real Python has a great tutorial on the subject of transactions. While written for

Django 1.6, much of the material remains pertinent to this day. realpython.com/

blog/python/transaction-management-with-django-1-6

96

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 113227.8: Summary

7.8 Summary
In this chapter we went over different ways to query a project’s persistent data.

We recommend using indexes once there is a better feel for how the data actually works

throughout the project.

Now that we know how to store and index data, let’s begin to display it. Starting with the

next chapter we’re diving into views!

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

97

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 11322
