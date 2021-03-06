import re

from bs4 import BeautifulSoup
from django.contrib.auth import authenticate,login
#from django.contrib.auth.views import login
from django.contrib.auth.decorators import login_required
from django.db.models import Q, F
from django.urls import reverse
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
# from django.views.decorators.csrf import csrf_exempt

from blog.forms import PostForm, LoginForm
from .models import Post

from tagging.models import Tag
from tagging.models import TaggedItem

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


def tag_search(request,pk,pagenum=None):
    queryset_list = TaggedItem.objects.get_by_model(Post,pk)
    all = Tag.objects.usage_for_model(Post,filters=dict(status='published'), counts=True)
      # Show 25 contacts per page

    if pagenum is None:
        page = 1
    else:
        page = int(pagenum)
    paginator = Paginator(queryset_list, 3)
    try:
        queryset = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        queryset = paginator.page(page)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        queryset = paginator.page(paginator.num_pages)
    return render(request, 'blog/search_results.html', {'posts': queryset, 'query': pk,'all':all})

def search(request):
    error = False
    if 'q' in request.GET:
        q = request.GET['q']
        if not q:
            error = True
        else:
            # posts= Post.objects.all()
            # for post in posts:
            #     print(post.tags)
            # queryset_list = TaggedItem.objects.get_by_model(Post, q)
            queryset_list = Post.published.filter(Q(title__icontains=q)|Q(tags__icontains=q))
            all = Tag.objects.usage_for_model(Post,filters=dict(status='published'), counts=True)

            paginator = Paginator(queryset_list, 4)  # Show 25 contacts per page

            page = request.GET.get('page')
            try:
                queryset = paginator.page(page)
            except PageNotAnInteger:
                # If page is not an integer, deliver first page.
                queryset = paginator.page(1)
            except EmptyPage:
                # If page is out of range (e.g. 9999), deliver last page of results.
                queryset = paginator.page(paginator.num_pages)
            return render(request, 'blog/search_results.html', {'posts': queryset, 'query': q,'all':all})
    return render(request, 'blog/search_form.html', {'error': error})


def post_list(request,pagenum=None):
    # posts = Post.objects.filter(published_date__lte=timezone.now())
    # house_tag = Tag.objects.all()
    queryset_list = Post.published.all()
    all=Tag.objects.usage_for_model(Post,filters=dict(status='published'),counts=True)

    if pagenum is None:
        page = 1
    else:
        page = int(pagenum)

    paginator = Paginator(queryset_list, 3)  # Show 5 contacts per page

    # page = request.GET.get('page')
    try:
        queryset = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        queryset = paginator.page(page)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        queryset = paginator.page(paginator.num_pages)


    return render(request, 'blog/post_list.html', {'posts': queryset,'all':all,'pagenum': pagenum})


def search_by_writer(request, writer,pagenum=None):
    queryset_list = Post.objects.filter(author__username=writer)
    all = Tag.objects.usage_for_model(Post, filters=dict(status='published'), counts=True)

    if pagenum is None:
        page = 1
    else:
        page = int(pagenum)

    paginator = Paginator(queryset_list, 3)  # Show 5 contacts per page

    # page = request.GET.get('page')
    try:
        queryset = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        queryset = paginator.page(page)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        queryset = paginator.page(paginator.num_pages)

    return render(request, 'blog/writers_post.html', {'posts': queryset,'writer':writer, 'all': all, 'pagenum': pagenum})

def post_detail(request,pk,slug):
    post = get_object_or_404(Post, slug=slug,pk=pk)
    if not request.user.is_authenticated:
        post.total_viewed = F('total_viewed') + 1
        post.save()
    #postprev=Post.objects.get(pk=post.pk-1)
    #postafter=Post.objects.get(pk=post.pk+1)
    tags=Tag.objects.get_for_object(post)
    all=Tag.objects.usage_for_model(Post,filters=dict(status='published'),counts=True)
    return render(request, 'blog/post_detail.html', {'post': post,'tags':tags,'all':all,})


@login_required
def post_new(request):
    if request.method == "POST":
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            if post.status == 'published':
                post.publish_time = timezone.now()

            soup = BeautifulSoup(post.text, 'html.parser')
            images = soup.find_all('img')
            para = soup.findAll(text=re.compile('^.+$'))
            para = " ".join(para)
            post.excerpt_text = para[0:500]
            # para = " ".join(para)
            if images:
                imageUrl = images[0].get('src')
                post.home_image = imageUrl

            #post.author = request.user
            #post.published_date = timezone.now()
            #if(post.published_status):
                #post.publish()
            post.save()
            print("saved to the databse")

            return HttpResponseRedirect(reverse('blog:dashboard'))
        else:
            return render(request, 'blog/post_edit.html', {'form': form})
    else:
        form = PostForm()
    return render(request, 'blog/post_edit.html', {'form': form})

@login_required
def post_edit(request, pk):

    if request.user.is_superuser:
        post = get_object_or_404(Post, pk=pk)

    else:
        query=Post.objects.filter(author=request.user)
        post = get_object_or_404(query, pk=pk)

    if request.method == "POST":
        form = PostForm(request.POST, instance=post)
        if form.is_valid():
            post = form.save(commit=False)
            if not post.publish_time:
                if post.status == 'published':
                    post.publish_time = timezone.now()

            soup = BeautifulSoup(post.text, 'html.parser')
            images = soup.find_all('img')
            para = soup.findAll(text=re.compile('^.+$'))
            para = " ".join(para)
            post.excerpt_text = para[0:500]
            # para = " ".join(para)
            if images:
                imageUrl = images[0].get('src')
                post.home_image = imageUrl


            post.updated = timezone.now()
            print("###################################")
            post.save()
            return HttpResponseRedirect(reverse('blog:dashboard'))

        else:
            return render(request, 'blog/post_edit.html', {'form': form})
            # return JsonResponse(form.errors,status=400)
    else:
        form = PostForm(instance=post)
    return render(request, 'blog/post_edit.html', {'form': form})


@login_required
def post_delete(request,pk):
    print("delete")
    instance = Post.objects.get(pk=pk)
    instance.delete()
    return HttpResponseRedirect(reverse('blog:dashboard'))


def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            user = authenticate(username=cd['username'],
                    password=cd['password'])
            if user is not None:
                if user.is_active:
                    login(request, user)
                    return HttpResponse('Authenticated '\
                        'successfully')
                else:
                    return HttpResponse('Disabled account')

            else:
                return HttpResponse('Invalid login')

    else:
        form = LoginForm()
    return render(request, 'blog/login.html', {'form': form})


@login_required
def dashboard(request):

    if request.user.is_superuser:
        queryset_list = Post.objects.all()
    else:
        queryset_list = Post.objects.filter(author__username=request.user.username)

    paginator = Paginator(queryset_list, 3)  # Show 25 contacts per page

    page = request.GET.get('page')
    try:
        queryset = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        queryset = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        queryset = paginator.page(paginator.num_pages)
    return render(request,
    'blog/dashboard.html',
    {'posts': queryset,})


