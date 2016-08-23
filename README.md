
# 情景
假设有一个操作，需要产生大量的计算，计算很消耗时间，并且需要把每次的计算结果在另一端存储起来。有一个传统的办法是通过多线程/多进程，但是这样的话这些计算还是在同一个机器上运行的，如果计算量很大的话，会给机器造成很大的压力，同时 ，也可能机器因为这些压力不能进行其他的服务。

# 方案
celery能很好的解决上面面临的问题，因为他是一个分布式的，我们可以把这些计算的请求都放在不同的机器上去执行，然后把计算结果交给后端一个统一的机器去处理。同时，如果发现其他的机器在计算的过程中也出现负载过高的情况下，还可以继续添加其他的机器过来处理。这样，分布式的优势就体现出来了，横向扩充能力很强大。

关于celery和rabbitmq的一些东西，可以先去他们的官网上了解下。

<a href="http://docs.jinkan.org/docs/celery/index.html" target="_blank">Celery</a>

<a href="https://www.rabbitmq.com" target="_blank">Rabbimq</a>

这些东西了解以后，现在就可以模拟下我们刚才情况，这里我画了一个拓扑图来，由于我这里的可用机器不多，就把这些机器放在同一个机器上面，道理是一样的：

![celery路由图](https://github.com/page1990/celery-simple-example/blob/master/route.png)

在上面的图里面，有一个类型是topic的交换机，通过绑定相应的key到三个不同的队列中，分别是default队列，compute队列，result队列。

然后有两个不同的方法，通过他们的队列和routing_key的配置，分别把消息放到了compute队列和result队列中。

# 代码结构

```
simple-example
├── celeryconfig.py
├── celeryconfig.pyc
├── tasks.py
└── tasks.pyc
```

celeryconfig.py是一个配置文件，里面定义了我们之前的交换机，队列和连接到broker这个中间人的配置：

```
BROKER_URL = 'amqp://localhost//'
CELERY_IMPORTS = ('tasks', )

CELERY_RESULT_BACKEND = 'amqp'
CELERY_RESULT_PERSISTENT = True
CELERY_TASK_RESULT_EXPIRES = None

CELERY_DEFAULT_QUEUE = 'default'
CELERY_QUEUES = {
    'default': {
        'binding_key': 'task.#',
    },
    'compute': {
        'binding_key': 'compute.#',
    },
    'result': {
        'binding_key': 'result.#',
    },
}
CELERY_DEFAULT_EXCHANGE = 'tasks'
CELERY_DEFAULT_EXCHANGE_TYPE = 'topic'
CELERY_DEFAULT_ROUTING_KEY = 'task.default'
CELERY_ROUTES = {
    'tasks.compute': {
        'queue': 'compute',
        'routing_key': 'compute.a_result'
    },
    'tasks.handle_result': {
        'queue': 'result',
        'routing_key': 'result.handle',
    },
}
```

接下来就是这个tasks.py的文件，里面定义了我们的要用celery的task要执行的东西:

```
from celery import Celery

app = Celery()

import celeryconfig

app.config_from_object(celeryconfig)

@app.task(ignore_result=True)
def handle_result(result):
    "Handle the result of compute."
    return result

@app.task(ignore_result=True)
def compute(x, y):
    "Perform a computation, calling another task to handle the results."
    return handle_result.delay(x * y).task_id
```

其中`app.config_from_object(celeryconfig)`这段代码表示这些task的配置使用celeryconfig.py里面的配置。

另外，compute函数的返回结果又是执行另外一个task函数，这个handle_result函数就是返回compute的结果。

可以这样理解，当生成了compute任务以后，把这个任务放到compute的队列中，同时，因为compute的返回也是执行另外的一个task，所以`handle_result`又会把这个任务放到result队列中。

# 运行

在`simple-example`的目录下，启动result worker:

```
celery worker -Q result --hostname=main -l debug
```

这样，这个worker就会专门处理result队列里面的东西

打开多个终端，在这些终端还是`simple-example`的目录下，启动多个compute worker:

```
celery worker -Q compute --hostname=compute1 -l debug
celery worker -Q compute --hostname=compute2 -l debug
            ......
celery worker -Q compute --hostname=computeN -l debug
```


在另外的一个终端中，同样在`simple-example`的目录下，打开python shell，触发任务:

```
>>from tasks import compute
>>for x in range(1, 51):
...    for y in range(1, 51):
...          compute.delay(x, y)
...


<AsyncResult: 3201522a-c182-471c-afff-285b298493ff>
<AsyncResult: 1a2c9434-7784-42df-8542-896021aff1db>
<AsyncResult: 350b4451-d4a9-4f33-a6c6-45d6094a9760>
<AsyncResult: 99c22b58-8699-4fb8-b9cf-03f1ce45b77b>
<AsyncResult: 5942373d-b269-4f75-93a7-3b9371670014>
<AsyncResult: d7a4dd74-c9aa-4c99-a271-56cc5bf95bfd>
<AsyncResult: 8bc9af3b-e13e-4abb-a884-000cd0e3d2dd>
<AsyncResult: a8e32146-0cce-48d5-9beb-d617be7e1e58>
<AsyncResult: a3e27bc5-e377-46b5-86b9-9338463e6bb3>
<AsyncResult: 429f7758-36f2-40c0-971c-7fa5cea9a5c7>
<AsyncResult: ca7a7d86-2fb0-46af-9a03-885e054b8457>
<AsyncResult: 27baea4d-b8b7-49d1-8378-e14dd5bdde0a>
<AsyncResult: f37c5c3f-8894-4188-9fc2-79b93334cb59>
<AsyncResult: 83a0b38e-5821-4ed9-8df0-83ac3e824503>
```

可以看到，生成了很多个异步的任务。

接下来看看worker里面的东西：

```
[2016-08-12 14:31:42,656: INFO/MainProcess] Task tasks.compute[f3c76e34-cea0-4f34-b5c2-073cf5d9dd71] succeeded in 0.00101957099832s: 'dc61b835-cdc3-47ea-8f1e-8593aeefef4a'
[2016-08-12 14:31:42,662: INFO/MainProcess] Received task: tasks.compute[a3fdc7bf-98e7-4dc7-90f4-8b9a45e8acb1]

[2016-08-12 14:31:42,675: INFO/MainProcess] Task tasks.compute[a3fdc7bf-98e7-4dc7-90f4-8b9a45e8acb1] succeeded in 0.00128307400155s: '85a50740-f65a-4ac5-b5e5-731886080b86'
[2016-08-12 14:31:42,676: DEBUG/MainProcess] Task accepted: tasks.compute[e345c7e0-82df-4980-8f0c-7f7d643df827] pid:18362
[2016-08-12 14:31:42,676: INFO/MainProcess] Task tasks.compute[e345c7e0-82df-4980-8f0c-7f7d643df827] succeeded in 0.000913791001949s: '6ee09f34-1a96-4f2b-827e-499239befb52'

[2016-08-12 14:31:42,612: INFO/MainProcess] Task tasks.compute[006f0e95-8422-4256-a045-b7382ec48e4e] succeeded in 0.000971367997408s: 'b5b06159-4bd9-4c75-9239-5907e5ca9eb5'
[2016-08-12 14:31:42,626: INFO/MainProcess] Received task: tasks.compute[cfba5499-79fe-48f1-af18-3b4e6947996e]
```

可以看到，处理compute队列的worker，不断刷着`Received task`和`succeeded`之类的消息，在不同的compute worker终端里面也看到类似的调试信息，说明多个worker取出了compute队列里面的任务并且执行了

同样的，在result队列的worker终端里面的消息：

```
[2016-08-12 14:31:44,405: INFO/MainProcess] Task tasks.handle_result[cb1a5424-a9bf-4299-bae8-66e80d7dd65e] succeeded in 0.00115526500304s: 2000
[2016-08-12 14:31:44,405: INFO/MainProcess] Received task: tasks.handle_result[0c45382f-5d5b-473c-8e9e-72f24bad99ae]

[2016-08-12 14:31:44,406: INFO/MainProcess] Task tasks.handle_result[6582d0a9-3b0b-4ad4-99c4-abd28d51703c] succeeded in 0.000763866002671s: 2350
[2016-08-12 14:31:44,407: INFO/MainProcess] Received task: tasks.handle_result[9a879ef5-88dc-4b23-a8a4-e6fe53e33703]
```

也可以看到执行了`handle_result`的任务。

#总结
Celery这个东西还是很强大的，因为他是一个基于python开发的分布式系统，并且可以使用很多broker，比如数据库，redis,不过官方的推荐是rabbimq这个强大的消息队列服务。

在实际的应用中，我们还可以自定义队列，这样，应用的任务可以在不同的机器上运行，横向扩展能力很强大。
