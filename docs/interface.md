# Interface
This application is not intended to be a web application, open to the world for perusing. However, it does have a simple interface to monitor batches, and check the status of the watcher. This interface can be modified as needed, depending on the needs of the user (the developer or administrator of the server). Thus, we suggest taking the following steps:

 - **Limit ip address**: Limit the ip addresses that can access the application to those in the range of your group.
 - **Passwords**: Make sure to set a lockdown password, so if someone accesses the web interface from within your group (that should not be) it is still protected.

There isn't any sort of button provided in the interface to do anything, so likely these precautions are just to (generally) keep things private.

# Dashboard
For the dashboard and settings views, you will notice the interface "jump" every 10 seconds. This is because it automatically refreshes itself, to show updates if there are any.


## Watcher Status
The watcher status is determined by the presence of absence of the pid file, and will show you the status in the interface if active:

![img/watcher_active.png](img/watcher_active.png)

or inactive:

![img/watcher_inactive.png](img/watcher_inactive.png)


## Batches
The dashboard also shows basic info about the batches. In the above pictures, there are none. In the picture below, there is one new batch. 

![img/dashboard.png](img/dashboard.png)

Given that a batch has errors, there will be a link to inspect the specific error message (the error tracking is implemented, but not yet the view).

Next, learn about usage by reading about the [manager](manager.md).


# API
It might be desired at some point to have the application be able to talk to others, so it has a simple API to serve batches and images, each as resources. 

![img/api.png](img/api.png)


## Resources
Per typical rest api, the following returns a paginated result of all resources, with links to `next` and `previous`, along with a `count`, and a list of `results` objects, each corresponding with one model. The api endpoints might look like this:

```
/api/images
/api/batches
```

and visually, it looks like this:

![img/api_detail.png](img/api_detail.png)

This means that, to query a specific page you would do:

```
/api/images?page=2
```

and again, this entire interface is behind the lockdown password, and can have additional authentication or changes if needed.


## Swagger
If the user (the administrators of the endpoint) want to interact or query dynamically, a swagger endpoint is provided:

![img/swagger.png](img/swagger.png)

And it generally explains the resources.


![img/swagger_details.png](img/swagger_details.png)
