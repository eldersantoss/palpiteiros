10 | Best Practices
Views

for Class-Based

Django provides a standard way to write class-based views (CBVs). In fact, as we mentioned

in previous chapters, a Django view is just a callable that accepts a request object and returns

a response. For function-based views (FBVs), the view function is that callable. For CBVs,

the view class provides an as_view() class method that returns the callable. This mecha-

nism is implemented in django.views.generic.View. All CBVs should inherit from
that class, directly or indirectly.

Django also provides a series of generic class-based views (GCBVs) that implement com-

mon patterns found in most web projects and illustrate the power of CBVs.

PACKAGE TIP: Filling the Missing Parts of Django GCBVs

Out of the box, Django does not provide some very useful mixins for GCBVs. The

django-braces library addresses most of these issues. It provides a set of clearly

coded mixins that make Django GCBVs much easier and faster to implement. The

library is so useful that three of its mixins have been copied into core Django.

10.1 Guidelines When Working With CBVs

(cid:228) Less view code is better.

(cid:228) Never repeat code in views.

(cid:228) Views should handle presentation logic. Try to keep business logic in models when

possible, or in forms if you must.

(cid:228) Keep your views simple.

(cid:228) Keep your mixins simpler.

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

121

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 11322Chapter 10: Best Practices for Class-Based Views

TIP: Familarize Yourself With ccbv.co.uk

Arguably this should be placed as the sixth guideline, ccbv.co.uk is so useful that

we felt it deserved its own tipbox. This site takes all the attributes and methods

that every CBV defines or inherits and flattens it into one comprehensive page per
view. Most Django developers, once they get past the tutorials on CBVs, rely on

ccbv.co.uk more than the official documentation.

10.2 Using Mixins With CBVs
Think of mixins in programming along the lines of mixins in ice cream: you can enhance

any ice cream flavor by mixing in crunchy candy bits, sliced fruit, or even bacon.

Figure 10.1: Popular and unpopular mixins used in ice cream.

Soft serve ice cream greatly benefits from mixins: ordinary vanilla soft serve turns into birth-

day cake ice cream when sprinkles, blue buttercream icing, and chunks of yellow cake are

mixed in.

In programming, a mixin is a class that provides functionality to be inherited, but isn’t meant

for instantiation on its own. In programming languages with multiple inheritance, mixins

can be used to add enhanced functionality and behavior to classes.

We can use the power of mixins to compose our own view classes for our Django apps.

When using mixins to compose our own view classes, we recommend these rules of in-

heritance provided by Kenneth Love. The rules follow Python’s method resolution order,

122

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 1132210.3: Which Django GCBV Should Be Used for What Task?

which in the most simplistic definition possible, proceeds from left to right:

1 The base view classes provided by Django always go to the right.

2 Mixins go to the left of the base view.

3 Mixins should not inherit from any other class. Keep your inheritance chain simple!

Example of the rules in action:

Example 10.1: Using Mixins in a View

from django.views.generic import TemplateView

class FreshFruitMixin:

def get_context_data(self, **kwargs):

context = super().get_context_data(**kwargs)

context["has_fresh_fruit"] = True

return context

class FruityFlavorView(FreshFruitMixin, TemplateView):

template_name = "fruity_flavor.html"

In our

rather

silly example,

the FruityFlavorView class

inherits

from both

FreshFruitMixin and TemplateView.

Since TemplateView is the base view class provided by Django, it goes on the far right

(rule 1), and to its left we place the FreshFruitMixin (rule 2). This way we know that our

methods and properties will execute correctly.

10.3 Which Django GCBV Should Be Used for What

Task?

The power of generic class-based views comes at the expense of simplicity: GCBVs come

with a complex inheritance chain that can have up to eight superclasses on import. Trying to

work out exactly which view to use or which method to customize can be very challenging

at times.

To mitigate this challenge, here’s a handy chart listing the name and purpose of each Django

CBV. All views listed here are assumed to be prefixed with django.views.generic.

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

123

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 11322Chapter 10: Best Practices for Class-Based Views

Purpose
Base view or handy view
that can be used for any-
thing.

Two Scoops Example
Section 10.6:
See
Using
Just
django.views.generic.View.

Name
View

RedirectView

TemplateView

ListView
DetailView

Redirect user to another
URL
Display a Django HTML
template.
List objects
Display an object

FormView

Submit a form

CreateView

Create an object

UpdateView

Update an object

DeleteView

Delete an object

Generic date views

For display of objects that
occur over a range of time.

Send users who visit ‘/log-
in/’ to ‘/login/’.
The ‘/about/’ page of our
site.
List of ice cream flavors.
Details on an ice cream fla-
vor.
The site’s contact or email
form.
Create a new ice cream fla-
vor.
Update
cream flavor.
Delete an unpleasant ice
cream flavor like Vanilla
Steak.
Blogs are a common rea-
son to use them. For Two
Scoops, we could create a
public history of when fla-
vors have been added to the
database.

an existing ice

Table 10.1: Django CBV Usage Table

124

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 1132210.4: General Tips for Django CBVs

TIP: The Three Schools of Django CBV/GCBV Usage

We’ve found that there are three major schools of thought around CBV and GCBV

usage. They are:

The School of “Use all the generic views!”

This school of thought is based on the idea that since Django provides functionality

to reduce your workload, why not use that functionality? We tend to belong to

this school of thought, and have used it to great success, rapidly building and then

maintaining a number of projects.

The School of “Just use django.views.generic.View”

This school of thought is based on the idea that the base Django CBV does just

enough and is ‘the True CBV, everything else is a Generic CBV’. In the past year,

we’ve found this can be a really useful approach for tricky tasks for which the

resource-based approach of “Use all the views” breaks down. We’ll cover some use

cases for it in this chapter.

The School of “Avoid them unless you’re actually subclassing views”

Jacob Kaplan-Moss says, “My general advice is to start with function views since

they’re easier to read and understand, and only use CBVs where you need them.
Where do you need them? Any place where you need a fair chunk of code to be

reused among multiple views.”

We generally belong to the first school, but it’s good for you to know that there’s no

real consensus on best practices here.

10.4 General Tips for Django CBVs
This section covers useful tips for all or many Django CBV and GCBV implementations.

We’ve found they expedite writing of views, templates, and their tests. These techniques

will work with Class-Based Views or Generic Class-Based Views. As always for CBVs in

Django, they rely on object oriented programming techniques.

10.4.1 Constraining Django CBV/GCBV Access to Authenticated

Users

The Django CBV documentation gives

a helpful working example of using

the

django.contrib.auth.decorators.login_required

decorator

with

a CBV, but

this example violates

the rule of keeping logic out of urls.py:

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

125

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 11322Chapter 10: Best Practices for Class-Based Views

docs.djangoproject.com/en/3.2/topics/class-based-views/intro/

#decorating-class-based-views.

Fortunately, Django provides a ready implementation of a LoginRequiredMixin object

that you can attach in moments. For example, we could do the following in all of the Django

GCBVs that we’ve written so far:

Example 10.2: Using LoginRequiredMixin

# flavors/views.py

from django.contrib.auth.mixins import LoginRequiredMixin

from django.views.generic import DetailView

from .models import Flavor

class FlavorDetailView(LoginRequiredMixin, DetailView):

model = Flavor

TIP: Don’t Forget the GCBV Mixin Order!

Remember that:

(cid:228) LoginRequiredMixin must always go on the far left side.

(cid:228) The base view class must always go on the far right side.

If you forget and switch the order, you will get broken or unpredictable results.

WARNING: Overriding dispatch() When Using LoginRequired-
Mixin

If you use LoginRequiredMixin and override the dispatch method, make

sure that the first thing you do is call super().dispatch(request, *args,

**kwargs). Any code before the super() call is executed even if the user is not

authenticated.

10.4.2 Performing Custom Actions on Views With Valid Forms

When you need to perform a custom action on a view with a valid form, the form_valid()

method is where the GCBV workflow sends the request.

126

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 1132210.4: General Tips for Django CBVs

Example 10.3: Custom Logic with Valid Forms

from django.contrib.auth.mixins import LoginRequiredMixin

from django.views.generic import CreateView

from .models import Flavor

class FlavorCreateView(LoginRequiredMixin, CreateView):

model = Flavor

fields = ['title', 'slug', 'scoops_remaining']

def form_valid(self, form):

# Do custom logic here

return super().form_valid(form)

To perform custom logic on form data that has already been validated, simply

add the logic to form_valid(). The return value of form_valid() should be a

django.http.HttpResponseRedirect.

10.4.3 Performing Custom Actions on Views With Invalid Forms

When you need to perform a custom action on a view with an invalid form, the

form_invalid() method is where the Django GCBV workflow sends the request. This

method should return a django.http.HttpResponse.

Example 10.4: Overwriting Behavior of form_invalid

from django.contrib.auth.mixins import LoginRequiredMixin

from django.views.generic import CreateView

from .models import Flavor

class FlavorCreateView(LoginRequiredMixin, CreateView):

model = Flavor

def form_invalid(self, form):

# Do custom logic here

return super().form_invalid(form)

Just as you can add logic to form_valid(), you can also add logic to form_invalid().

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

127

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 11322Chapter 10: Best Practices for Class-Based Views

You’ll see an example of overriding both of these methods in Section 13.5.1: ModelForm

Data Is Saved to the Form, Then the Model Instance.

Figure 10.2: The other CBV: class-based vanilla ice cream.

10.4.4 Using the View Object

If you are using class-based views for rendering content, consider using the view object

itself to provide access to properties and methods that can be called by other methods and

properties. They can also be called from templates. For example:

Example 10.5: Using the View Object

from django.contrib.auth.mixins import LoginRequiredMixin

from django.utils.functional import cached_property

from django.views.generic import UpdateView, TemplateView

from .models import Flavor

from .tasks import update_user_who_favorited

class FavoriteMixin:

@cached_property

def likes_and_favorites(self):

"""Returns a dictionary of likes and favorites"""

128

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 1132210.4: General Tips for Django CBVs

likes = self.object.likes()

favorites = self.object.favorites()

return {

"likes": likes,

"favorites": favorites,

"favorites_count": favorites.count(),

}

class FlavorUpdateView(LoginRequiredMixin, FavoriteMixin,

,→

UpdateView):

model = Flavor

fields = ['title', 'slug', 'scoops_remaining']

def form_valid(self, form):

update_user_who_favorited(

instance=self.object,

favorites=self.likes_and_favorites['favorites']

)

return super().form_valid(form)

class FlavorDetailView(LoginRequiredMixin, FavoriteMixin,

,→

TemplateView):

model = Flavor

The nice thing about this is the various flavors/ app templates can now access this property:

Example 10.6: Using View Methods in flavors/base.html

{# flavors/base.html #}

{% extends "base.html" %}

{% block likes_and_favorites %}

<ul>

<li>Likes: {{ view.likes_and_favorites.likes }}</li>

<li>Favorites: {{ view.likes_and_favorites.favorites_count

,→

}}</li>

</ul>

{% endblock likes_and_favorites %}

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

129

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 11322Chapter 10: Best Practices for Class-Based Views

10.5 How GCBVs and Forms Fit Together
A common source of confusion with GCBVs is their usage with Django forms.

Using our favorite example of the ice cream flavor tracking app, let’s chart out a couple of

examples of how form-related views might fit together.

First, let’s define a flavor model to use in this section’s view examples:

Example 10.7: Flavor Model

# flavors/models.py

from django.db import models

from django.urls import reverse

class Flavor(models.Model):

class Scoops(models.IntegerChoices)

SCOOPS_0 = 0

SCOOPS_1 = 1

title = models.CharField(max_length=255)

slug = models.SlugField(unique=True)

scoops_remaining = models.IntegerField(choices=Scoops.choices,

default=Scoops.SCOOPS_0)

def get_absolute_url(self):

return reverse("flavors:detail", kwargs={"slug":

,→

self.slug})

Now, let’s explore some common Django form scenarios that most Django users run into

at one point or another.

10.5.1 Views + ModelForm Example

This is the simplest and most common Django form scenario. Typically when you create a
model, you want to be able to add new records and update existing records that correspond

to the model.

In this example, we’ll show you how to construct a set of views that will create, update and

display Flavor records. We’ll also demonstrate how to provide confirmation of changes.

Here we have the following views:

130

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 1132210.5: How GCBVs and Forms Fit Together

1 FlavorCreateView corresponds to a form for adding new flavors.

2 FlavorUpdateView corresponds to a form for editing existing flavors.

3 FlavorDetailView corresponds to the confirmation page for both flavor creation and

flavor updates.

To visualize our views:

Figure 10.3: Views + ModelForm Flow

Note

that we

stick as

closely

as possible

to Django naming conventions.

FlavorCreateView subclasses Django’s CreateView, FlavorUpdateView subclasses

Django’s UpdateView, and FlavorDetailView subclasses Django’s DetailView.

Writing these views is easy, since it’s mostly a matter of using what Django gives us:

Example 10.8: Building Views Quickly with CBVs

# flavors/views.py

from django.contrib.auth.mixins import LoginRequiredMixin

from django.views.generic import CreateView, DetailView, UpdateView

from .models import Flavor

class FlavorCreateView(LoginRequiredMixin, CreateView):

model = Flavor

fields = ['title', 'slug', 'scoops_remaining']

class FlavorUpdateView(LoginRequiredMixin, UpdateView):

model = Flavor

fields = ['title', 'slug', 'scoops_remaining']

class FlavorDetailView(DetailView):

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

131

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 11322Chapter 10: Best Practices for Class-Based Views

model = Flavor

Simple at first glance, right? We accomplish so much with just a little bit of code!

But wait, there’s a catch. If we wire these views into a urls.py module and create the necessary

templates, we’ll uncover a problem:

The FlavorDetailView is not a confirmation page.

For now, that statement is correct. Fortunately, we can fix it quickly with a few modifications

to existing views and templates.

The first step in the fix is to use django.contrib.messages to inform the user visiting

the FlavorDetailView that they just added or updated the flavor.

We’ll

need

to

override

the

FlavorCreateView.form_valid()

and

FlavorUpdateView.form_valid() methods. We can do this conveniently for

both views with a FlavorActionMixin.

For the confirmation page fix, we change flavors/views.py to contain the following:

Example 10.9: Success Message Example

# flavors/views.py

from django.contrib import messages

from django.contrib.auth.mixins import LoginRequiredMixin

from django.views.generic import CreateView, DetailView, UpdateView

from .models import Flavor

class FlavorActionMixin:

fields = ['title', 'slug', 'scoops_remaining']

@property

def success_msg(self):

return NotImplemented

def form_valid(self, form):

messages.info(self.request, self.success_msg)

return super().form_valid(form)

132

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 1132210.5: How GCBVs and Forms Fit Together

class FlavorCreateView(LoginRequiredMixin, FlavorActionMixin,

CreateView):

model = Flavor

success_msg = "Flavor created!"

class FlavorUpdateView(LoginRequiredMixin, FlavorActionMixin,

UpdateView):

model = Flavor

success_msg = "Flavor updated!"

class FlavorDetailView(DetailView):

model = Flavor

Earlier in this chapter, we covered a simpler example of how to override form_valid()

within a GCBV. Here, we reuse a similar form_valid() override method by creating a

mixin to inherit from in multiple views.

Now we’re using Django’s messages framework to display confirmation messages to the

user upon every successful add or edit. We define a FlavorActionMixin whose job is to

queue up a confirmation message corresponding to the action performed in a view.

TIP: This replicates SuccessMessageMixin

Since we wrote

this

section

in

2013, Django

has

implemented

django.contrib.messages.views.SuccessMessageMixin, which

pro-

vides similar functionality.

Reference:

https://docs.djangoproject.com/en/3.2/ref/contrib/

messages/#django.contrib.messages.views.SuccessMessageMixin

TIP: Mixins Shouldn’t Inherit From Other Object

Please take notice that the FlavorActionMixin is a base class, not inheriting from

another class in our code rather than a pre-existing mixin or view. It’s important that

mixins have as shallow inheritance chain as possible. Simplicity is a virtue!

After a flavor is created or updated, a list of messages is passed to the context of the

FlavorDetailView. We can see these messages if we add the following code to the views’

template and then create or update a flavor:

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

133

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 11322Chapter 10: Best Practices for Class-Based Views

Example 10.10: flavor_detail.html

{% if messages %}

<ul class="messages">

{% for message in messages %}

<li id="message_{{ forloop.counter }}"

{% if message.tags %} class="{{ message.tags }}"

{% endif %}>

{{ message }}

</li>

{% endfor %}

</ul>

{% endif %}

TIP: Reuse the Messages Template Code!

It is common practice to put the above code into your project’s base HTML tem-

plate. Doing this allows message support for templates in your project.

To recap, this example demonstrated yet again how to override the form_valid() method,

incorporate this into a mixin, how to incorporate multiple mixins into a view, and gave a

quick introduction to the very useful django.contrib.messages framework.

10.5.2 Views + Form Example

Sometimes you want to use a Django Form rather than a ModelForm. Search forms are a

particularly good use case for this, but you’ll run into other scenarios where this is true as

well.

In this example, we’ll create a simple flavor search form. This involves creating an HTML

form that doesn’t modify any flavor data. The form’s action will query the ORM, and the

records found will be listed on a search results page.

Our intention is that when using our flavor search page, if users do a flavor search for

“Dough”, they should be sent to a page listing ice cream flavors like “Chocolate Chip Cookie

Dough,” “Fudge Brownie Dough,” “Peanut Butter Cookie Dough,” and other flavors con-

taining the string “Dough” in their title. Mmm, we definitely want this feature in our web

application.

There are more complex ways to implement this, but for our simple use case, all we need is

a single view. We’ll use a FlavorListView for both the search page and the search results

134

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 1132210.5: How GCBVs and Forms Fit Together

page.

Here’s an overview of our implementation:

Figure 10.4: Views + Form Flow

In this scenario, we want to follow the standard internet convention for search pages, where

‘q’ is used for the search query parameter. We also want to accept a GET request rather than

a POST request, which is unusual for forms but perfectly fine for this use case. Remember,

this form doesn’t add, edit, or delete objects, so we don’t need a POST request here.

To return matching search results based on the search query, we need to modify the

standard queryset supplied by the ListView. To do this, we override the ListView's

get_queryset() method. We add the following code to flavors/views.py:

Example 10.11: List View Combined with Q Search

from django.views.generic import ListView

from .models import Flavor

class FlavorListView(ListView):

model = Flavor

def get_queryset(self):

# Fetch the queryset from the parent get_queryset

queryset = super().get_queryset()

# Get the q GET parameter

q = self.request.GET.get("q")

if q:

# Return a filtered queryset

return queryset.filter(title__icontains=q)

# Return the base queryset

return queryset

Now, instead of listing all of the flavors, we list only the flavors whose titles contain the

search string.

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

135

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 11322Chapter 10: Best Practices for Class-Based Views

As we mentioned, search forms are unusual in that unlike nearly every other HTML form

they specify a GET request in the HTML form. This is because search forms are not chang-

ing data, but simply retrieving information from the server. The search form should look

something like this:

Example 10.12: Search Snippet of HTML

{# templates/flavors/_flavor_search.html #}

{% comment %}

Usage: {% include "flavors/_flavor_search.html" %}

{% endcomment %}

<form action="{% url "flavor_list" %}" method="GET">

<input type="text" name="q" />

<button type="submit">search</button>

</form>

TIP: Specify the Form Target in Search Forms

We also take care to specify the URL in the form action, because we’ve found that

search forms are often included in several pages. This is why we prefix them with ‘_’

and create them in such a way as to be included in other templates.

Once we get past overriding the ListView's get_queryset() method, the rest of this

example is just a simple HTML form. We like this kind of simplicity.

10.6 Using Just django.views.generic.View
It’s entirely possible to build a project just using django.views.generic.View for all the

views. It’s not as extreme as one might think. For example, if we look at the official Django

documentation’s introduction to class-based views (docs.djangoproject.com/en/3.

2/topics/class-based-views/intro/#using-class-based-views), we can see

the approach is very close to how function-based views are written. In fact, we highlighted

this two chapters ago in Section 8.6.1: The Simplest Views because it’s important.

Imagine instead of writing function-based views with nested-ifs representing different

HTTP methods or class-based views where the HTTP methods are hidden behind

get_context_data() and form_valid() methods, they are readily accessible to de-

velopers. Imagine something like:

136

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 1132210.6: Using Just django.views.generic.View

Example 10.13: Using the Base View Class

from django.contrib.auth.mixins import LoginRequiredMixin

from django.shortcuts import get_object_or_404

from django.shortcuts import render, redirect

from django.views.generic import View

from .forms import FlavorForm

from .models import Flavor

class FlavorView(LoginRequiredMixin, View):

def get(self, request, *args, **kwargs):

# Handles display of the Flavor object

flavor = get_object_or_404(Flavor, slug=kwargs['slug'])

return render(request,

"flavors/flavor_detail.html",

{"flavor": flavor}

)

def post(self, request, *args, **kwargs):

# Handles updates of the Flavor object

flavor = get_object_or_404(Flavor, slug=kwargs['slug'])

form = FlavorForm(request.POST, instance=flavor)

if form.is_valid():

form.save()

return redirect("flavors:detail", flavor.slug)

While we can do this in a function-based view, it can be argued that the GET/POST

method declarations within the FlavorView are easier to read than the traditional “if

request.method == ...” conditions. In addition, since the inheritance chain is so shal-

low, it means using mixins doesn’t threaten us with cognitive overload.

What we find really useful, even on projects which use a lot of generic class-based views, is

using the django.views.generic.View class with a GET method for displaying JSON,

PDF or other non-HTML content. All the tricks that we’ve used for rendering CSV, Excel,

and PDF files in function-based views apply when using the GET method. For example:

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

137

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 11322Chapter 10: Best Practices for Class-Based Views

Example 10.14: Using the View Class to Create PDFs

from django.contrib.auth.mixins import LoginRequiredMixin

from django.http import HttpResponse

from django.shortcuts import get_object_or_404

from django.views.generic import View

from .models import Flavor

from .reports import make_flavor_pdf

class FlavorPDFView(LoginRequiredMixin, View):

def get(self, request, *args, **kwargs):

# Get the flavor

flavor = get_object_or_404(Flavor, slug=kwargs['slug'])

# create the response

response = HttpResponse(content_type='application/pdf')

# generate the PDF stream and attach to the response

response = make_flavor_pdf(response, flavor)

return response

This is a pretty straight-forward example, but if we have to leverage more mixins and deal

with more custom logic, the simplicity of django.views.generic.View makes it much

easier than the more heavyweight views. In essence, we get all the advantages of function-

based views combined with the object-oriented power that CBVs give us.

10.7 Additional Resources

(cid:228) docs.djangoproject.com/en/3.2/topics/class-based-views/

(cid:228) docs.djangoproject.com/en/3.2/topics/class-based-views/

generic-display/

(cid:228) docs.djangoproject.com/en/3.2/topics/class-based-views/

generic-editing/

(cid:228) docs.djangoproject.com/en/3.2/topics/class-based-views/mixins/

(cid:228) docs.djangoproject.com/en/3.2/ref/class-based-views/

(cid:228) The GCBV inspector at ccbv.co.uk

(cid:228) python.org/download/releases/2.3/mro/ - For Python 2.3, nevertheless an

excellent guide to how Python handles MRO.

(cid:228) daniel.feldroy.com/tag/class-based-views.html

138

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 1132210.8: Summary

(cid:228) spapas.github.io/2018/03/19/comprehensive-django-cbv-guide/

-

Serafeim Papastefanos’ lovely deep dive into Django CBVs

(cid:228) djangodeconstructed.com/2020/04/27/roll-your-own-class-based-views-in-django/

- Another deep dive into CBVs, this one illustrating how to create a RESTful API

with DRF

PACKAGE TIP: Other Useful CBV Libraries

(cid:228) django-extra-views Another great CBV library, django-extra-views covers

the cases that django-braces does not.

(cid:228) django-vanilla-views A very interesting library that provides all the power of

classic Django GCBVs in a vastly simplified, easier-to-use package. Works

great in combination with django-braces.

10.8 Summary
This chapter covered:

(cid:228) Using mixins with CBVs

(cid:228) Which Django CBV should be used for which task

(cid:228) General tips for CBV usage

(cid:228) Connecting CBVs to forms

(cid:228) Using the base django.views.generic.View

The next chapter explores asynchronous views. Chapter 12 explores common CBV/form

patterns. Knowledge of both of these are helpful to have in your developer toolbox.

Please submit issues to github.com/feldroy/two- scoops- of- django- 3.x/issues

139

Prepared exclusively for LAKLAK LAKLAK (39r4ye7vy@relay.firefox.com)  Transaction: 11322
