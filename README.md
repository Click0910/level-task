## Overview

For this demo, it was designed and implemented and async architecture in order to process Datasets and Make inference
in the data from the dataset.

In this demo, I focus mainly in architecture, distributed system and integrate a ML pipeline instead train models,
clean architectures or avoid data leakage etc.

For this demo are deployed in a docker-compose:

    -celery workers
    -Redis(acts as backend for RabbitMQ)
    -RabbitMQ
    -API
    -PostgresDB

Everything is deployed in isolated docker containers.
later in this document it will be explained the components and the architectural decision.

I've included a `variables.env`  file with dummy values strictly for demonstration purposes.
In a real-world or production environment, environment variables must never be stored or shared in `.env`  files.

Instead, secrets and sensitive configurations should be managed securely using tools like `AWS SSM Parameter Store` , `Secrets Manager`, 
or any appropriate vault solution.

These values should then be injected into the operating system environment at runtime — for example, via your deployment pipeline, 
container orchestration system (like `ECS/EKS`), or startup scripts — ensuring that no credentials are ever hardcoded or 
committed to version control.

## Local SetUp instructions

### Prerequesites

This project needs docker >= 20 and docker-compose >= 1.29. Installation.

Also needs `make` in order to execute make commands (make acts like an orchestrator for local setUp)

Ensure to have installed the prerequisites in your local environment.

### Optional.

`Docker-desktop` . I know that is not as stable like using the CLI, but I'm pro GUI (graphic interfaces), so helps a lot.

----------------------

### Build

Run this before you run any other make commands to ensure you have build the images.

```sh
make build
```

### Run

```sh
make up
```

### Test

Before running tests remember to build the project.


```sh
make test
```

### Finish

```sh
make down
```

### Architecture

As was mentioned before, for this project are used Message broker and queues (RabbitMQ), consumers (celery workers),
API (fastAPI), broker-backend (Redis) and DB (PostgresSQL).

The complete flow you can check in the next diagrams:

```mermaid
graph TD
    subgraph API_FastAPI["API FastAPI"]
        A1["POST /requests<br/>(new ticket)"] --> C1["send_task:<br/>process_new_ticket"]
        A2["POST /seed"] --> C2["send_task:<br/>seed_database"]
        A3["POST /process-tickets"] --> C3["send_task:<br/>process_existing_ticket"]
        A4["GET /requests/{id}"] --> C4["send_task:<br/>fetch_record"]
        A5["GET /requests?category=..."] --> C5["send_task:<br/>filter_by_category"]
        A6["GET /status/{task_id}"] --> C6["AsyncResult lookup"]
    end

    subgraph Celery_Broker["Celery Broker (RabbitMQ)"]
        C1 --> Q1["ticket_queue"]
        C2 --> Q1
        C3 --> Q1
        C4 --> Q1
        C5 --> Q1
        C7["send_task:<br/>run_inference"] --> Q2["inference_queue"]
    end

    subgraph Worker_ticket_worker["Worker ticket_worker"]
        Q1 --> W1["process_new_ticket"]
        Q1 --> W2["seed_database"]
        Q1 --> W3["process_existing_ticket"]
        Q1 --> W4["fetch_record"]
        Q1 --> W5["filter_by_category"]
        W1 --> C7
    end

    subgraph Worker_inference_worker["Worker inference_worker"]
        Q2 --> W6["run_inference"]
        W6 --> DB1[(PostgreSQL)]
    end

    subgraph Database["Database"]
        DB1[(PostgreSQL)]
    end

    style API_FastAPI fill:#e0f7fa,stroke:#00796b
    style Celery_Broker fill:#f1f8e9,stroke:#689f38
    style Worker_ticket_worker fill:#fff3e0,stroke:#f57c00
    style Worker_inference_worker fill:#fce4ec,stroke:#c2185b
    style Database fill:#ede7f6,stroke:#512da8
```



```mermaid
graph LR
    A[Cliente] -->|POST /requests| B[FastAPI]
    B -->|Mensaje: ticket_data| C[RabbitMQ<br>Cola 1: raw_tickets]
    C --> D[Celery Worker I/O]
    D -->|1. Guardar en DB| E[(PostgreSQL)]
    D -->|2. Preparar datos| F[RabbitMQ<br>Cola 2: inference_queue]
    F --> G[Celery Worker Inferencia]
    G -->|3. Clasificar| H[Modelo ML]
    H -->|4. Resultados| E
```



```mermaid
sequenceDiagram
    participant Cliente
    participant FastAPI
    participant RabbitMQ
    participant CeleryIO as Celery Worker I/O
    participant PostgreSQL
    participant CeleryInf as Celery Worker Inferencia
    participant ModeloML
    
    Cliente->>FastAPI: POST /requests {ticket_data}
    activate FastAPI
    FastAPI->>FastAPI: Validar payload (Pydantic)
    FastAPI->>PostgreSQL: INSERT ticket (status=unprocessed)
    FastAPI->>RabbitMQ: publish(ticket_id) [queue: processing_queue]
    deactivate FastAPI
    FastAPI-->>Cliente: 202 Accepted + ticket_id
    
    RabbitMQ->>CeleryIO: consume(ticket_id) [from processing_queue]
    activate CeleryIO
    CeleryIO->>PostgreSQL: SELECT ticket_data
    CeleryIO->>CeleryIO: Preparar input: text = subject + body
    CeleryIO->>RabbitMQ: publish(inference_task) [queue: inference_queue]
    deactivate CeleryIO
    
    RabbitMQ->>CeleryInf: consume(inference_task) [from inference_queue]
    activate CeleryInf
    CeleryInf->>ModeloML: classify(text)
    ModeloML-->>CeleryInf: {category, confidence}
    CeleryInf->>PostgreSQL: UPDATE SET category, confidence, status=processed
    deactivate CeleryInf
```


As you can see, the flow is basically:

API -> RabbitMQ Ticket -> celery worker ticker -> RabbitMQ inference -> Celery inference.

- The API sends messages to the queue (ticket queue)
- Those messages in the queue are consumed by a worker (ticket worker)
- Worker (ticket worker) store data in the Db and send a message to another queue (inference queue)
- Worker (inference worker), consumes messages for the queue (inference queue)
- Worker (inference worker), makes the inference and store results in the DB (In fact execute a bit more tasks)

The reason of this is separate responsibilities and scalability. Also, I was looking for an async solution that could scale and process large datasets.

I will explore this in deep in Implementation  and why this? sections.

# How to use this project?

After execute the `make` commands I recommend to make this:

### seed.

In postman or using curls or using your preferred tool, make a request to:

`POST http://localhost:5000/seed`

This endpoint will copy the data from the data set into the DB.

After that execute:

### process-data
`POST http://localhost:5000/process-tickets`
with the payload:

```
{
    "batch_size": 2000
}
```
This will process the data from the db that was seed and hasn't processed before and make the inference.

### Process new ticket.

`POST http://localhost:5000/requests`

with a payload like this:


```
{
  "subject": "Error in billing system",
  "body": "Clients report that they cannot download their invoices when their press the download button in the billing portal",
  "priority": "High"
}
```

This will create a new record from scratch that is not presented in the dataset. Store the result in the DB.

### Fetch a ticket:

`GET http://localhost:5000/requests/{id}`

This return a payload with the ticket data

### Filter tickets.


`GET http://localhost:5000/requests?category=technical`

Fetch a list with the tickets filtered on base a query param, like technically or billing.

### Status Async Task.

When you execute endpoints like `POST /seed` or `POST /process-tickets`, in the background is executed an async
task using RabbitMQ and celery workers. Those endpoints return a `task_id`

Using that `task_id` you can make a request to:

`GET http://localhost:5000/status/{ticket_id}`

This endpoint return the status of the task, like PENDING, COMPLETED, FAILED.


**_Note_**: _For this demo you need to make requests manually to the endpoints using your preferred tool. In order to automate a bit more
the workflow, it can be implemented a jupyter notebook where is automated all the requests for a better client experience. for example
make peridically requests to `/status` to check the satus of the task. 
the notebook can be also deployed in an isolated container._

----------------------------------

# Implementation.

As I mentioned in the overview, for this demo, I focus mainly in the architecture, in how to process efficient datasets
and make inferences on the data.

To do this, I designed the architecture that is above and in order to implement it, I designed a distributed system (for this demo, deployed in a docker compose. For a real project,
this will be deployed in a cluster like `Kubernetes` or `AWS ECS fargate`). In this distributed system, everything is deply in isolated containers,
It was deployed:

## APi.

This is just an API that contains the next endpoints:

- `POST /seed` -> Seed the DB, Upload the data from the dataset to the DB.
- `POST /process-tickets` -> Process the tickets form the dataset that are seed in the DB with `POST /seed`. Make the inference for the tickets in the DB from the dataset.
- `POST /requests` -> Process new tickets that are not seed with `POST /seed`. Tickets that are not from the dataset. Make the inference.
- `GET /requests/{id}` -> Fetch a specific record from the DB on base id.
- `GET /requests?category={something}` -> Accepts query param and filter on base category.
- `GET /status/task_id `-> Check the status of an Async task.


Probably you have questions about, why `/seed`, why `/process-tickets`, why `/status/task_id`

I'll try to cover and answer the potential questions in section **why this**?

The container for the API is exposed in the port 5000.

## RabbitMQ (Message_broker)

As message broker I choose a RabbitMQ with two queues (apart from default queues that are provisioned with celery):

- `ticket_queue`
- `inference_queue`

Why those queues or why RabbitMQ? Answers in **why this?** section.

`RabbitMQ` is exposed in port `8080` and with the dummy credentials that you can found in `variables.env` file, you can access to
RabbitMQ portal to check the queues, messages etc.

## Celery workers.

`Celery` is the official consumer of `RabbitMQ` and has a native integration with it, so makes sense to use `celery workers` as consumer.

It was implemented two celery workers:

- `ticket_worker` -> in charge to process the data.
- `inference_worker` -> in charge to make mainly the inference.

Both workers are deployed in separated an isolated containers.

The reason of this is have fully decoupled of both process and scale independently.

I expand this in **why this?** section.

### ticket_worker:

It's the worker for process data and execute mainly I/O operations. For that reason the worker use `multithreading`, in this
case, native threads (threads handle by the OS). This worker is mainly in charge to upload the dataset into the DB (I/O operations)

The worker has different tasks (check the `/ticket_worker/worker.py`) and also fetch the data using batches (check `database.py`)

For memory optimization the data is fetched by batches and store the whole batch in a `List` in memory to be processed. 
This approach is good for small - medium datasets. 

For large datasets is developed a generator (currently is not used but can be used) in order to use the lazy evaluation 
and don't overload the memory/

### inference_worker.

The worker in charge of inference. When the image is build, the docker context download the CSV and make a basic training of a model in
`sckit-learn` and store the pretrain model in the same container.

The CSV used for make the classification is the same that was used for train the model. This of course leads a `data leakage` and this is a really bad practice in 
a real scenario. I've used this for simplicity and because the idea of this demo is shows the ML pipeline, instead focus un train models.

For a real scenario we need to use a pretrain model like GPT models, any pretrain model in Pytorch or something similar. Or train our own model 
but using a different CSV.

It's deployed in a docker container isolated, using the cpu for process (for this light model is fine). For a heavy model, we need to use parallelism
probably using the GPU cores using CUDA.

Also, for large model needs to be implemented a `Dataloader` who will load the data into the model for the inference. 
And probably isolate the load Data and charge the model in separate classes (improvements that we can do)


## Redis (celery_backend)

Redis acts just as the backend for the message broker, it's pretty common to use it for this.

## PostgresDB.

The DB to store the dataset, the result of the inference and new tickets also. Both workers are able to write in this DB.
It was implemented a schema for the DB using the file `src/database/sql/init.sql` (check for details)

The Postgres db is deployed in an Isolated container. The container is exposed in the `host-port 5432` (the postgres default one)
and like that you can use `pg-admin` or `Data-grip` (my favorite one) to explore the DB using the dummy credentials in `variables.env`
in order to connect into the DB and explore with a GUI the database.



-------------------------------------


# Why this?


## Why have endpoints like /seed or /status?

Basically, `/seed` are in charge to upload the dataset unto the DB. Is in charge to trigger this action. But why?

Basically the idea was to take advantage of the distributed system that was implemented for this demo and the async tasks to improve the performance of upload data.

The dataset used is relative small, but imagine something with hundred thousands or millions of rows. So, the idea was take advantage of the infra already setUp.

In a prod scenario these tasks can be trigger using an SDK or CLI command in order to avoid latency issues, but fot this demo I consider is ok have this endpoint.


## And what about `/status/task_id`?

Endpoints like `POST /seed` and `POST /process-tickets` execute under the hood async tasks using celery and RabbitMQ.

Since is an async task, celery only returns the data when the status of the task is "SUCCESS".

The idea of this endpoint is to check the status of the async tasks execute by the endpoints.


## What about /process-ticket and POST /requests?

I mentioned this before, but `/process-tickets` is in charge to  process the data from the dataset that is stored in the DB and 
`POST /request` in charge of process a new ticket (not present originally in the dataset).

Basically I think that the data from the dataset is mainly for training, so I would need another endpoint for new data.

so why two endpoint both makes similar things?

Well, yes this is true and probably there are some duplicate code (again, I focus mainly in architecture, this for sure needs to be refactored)
but the idea of this was had separate responsibilities. But this could be refactored for a real application if we think is needed.

## Why two workers isolated and two queues?

The reason of this in mainly for scalability.

The idea is separate processes in `data process` and `inference process`.

The reason of this is that `data process` in this context is mainly I/O operations (fetch in the DB, write in the DB etc.)

For the `inference process` its true that if you use a pretrained model, probably the operation is I/O. 
But this is valid for light models (like here that I made a basic training for a model using `scikit-learn`)
but, for large models (some of GPT for example), this operation is more `CPU bound`. So, in this context is worth to separate the responsibilities.

Having workers independent between them, allows to scale only the worker that you need and avoid bottlenecks.

Similar thing with the queues. Having separate queues for each worker, allows to access to the metrics of the queue (like `length of the queue` o `latency queue`) 
and in base of them decide scale in or scale out the workers.
If we use the same queue (that is viable) this scalability of the workers could be more complex.


## why using the same CSV for training and making predictions?

If you check the demo, the `inference_worker` train a `scikit-learn` model using the hugging face CSV. and then use the same CSV to make predictions.

This of course cause `data leakage`, and is not a good practice I know. But as I mentioned before, this is just a demo and I focussed mainly in the architecture of the ML pipeline.

I could use another pretrain model, but I just wanted something light for this demo.

In a real scenario we need to use a large pretrain model or train our own model but with another dataset.

## why rabbitMQ?

First for practicity. Configure a `RabbitMQ` as message broker is much simpler that configure another broker like `kafka`.

Second, the data is mainly static, so a protocol in base of queues is really good for this. For stream data, the solution will require something similar to kafka (or `AWS Kinesis`).
But for now and for this demo this works well.

Disadvantage of RabbitMQ is horizontal scalability of the queue, but for now I think is not a problem this 
(even in a real scenario in cloud we can use `AWS SQS` that scales in theory "infinite" and AWS takes care of it)


## Why of this architecture?

This distributed system is mainly thinking in scalability of the solution for process large datasets. 
The idea is scale each worker only when is needed. Havina clear and isolated separation of the components, we can scale all of them in am
independently way using the relevant metrics of each one.

## Why an sckit-learn model?

For practice and to use something light for this demo.


# Unit-Tests

It was implemented some simple unit test for a couple of endpoints. (check test folder)

Those endpoints only were tested with success cases.

In a real project needs to be tested all cases included fail cases. Also edge cases.

Also, in a real scenario is needed to test basically every implementation in the application. In this case it would be needed test the `celery workers`
with all the tasks and auxiliar functions.

For sure add unit test for everything would take probably days not just 4 hours.


-----------------

# AWS Migration.

The same architecture and the same principles in this design can be implemented using AWS.

Basically:
- instead of use `RabbitMQ` we can use `AWS SQS`. 
- Instead of `Celery Workers` we can use `AWS Lambdas`. 
- Instead of `PostgresSQL` we can use `AWS DynamoDB`.
- The API could be a lambda as well (but monitoring and taking care in don't exceed the lambda execution runtime.)
- `AWS SageMaker` family for train models

Is basically the same architecture, but serverless. This helps a lot in the maintainability and scalability of the solution,
since AWS take cares about maintain and scale the lambdas or SQS.


-----------------

# How to improve it?

The workers have som values by default. For example for `ticket_worker` I set up by default 2 instances of this and by default
each instance has 8 threads.

Using multiple threads here works because both tasks are mainly I/O operations (read and write the DB). Celery handle in background the threads and in python
multithreading for I/O operations is fine (it's a problem for CPU bound operations and real parallelism base on threads)



```
ticket_worker:
    build: ./src/workers/ticket
    env_file:
      - 'variables.env'
    environment:
      - CELERY_WORKER_CONCURRENCY=8
    links:
      - backend:backend
      - broker:broker
      - database:database
    depends_on:
      - broker
      - backend
      - database
    networks:
      - network
    command: celery -A worker.ticket_worker worker -P threads --loglevel=INFO --queues=ticket_queue
```

This works good, but for an optimize solution (and also a cost-efficient) this needs to scale on base of metrics.

In a real scenario, the relevant metrics for this would be `length of the queue`, `latency of the queue` and probably `memory`.

On base of those metrics we decided if scale in or out.

------------

Similar way to inference worker. I've set up  using some values by default. But the decision to scale should be on base of
queue metrics.

Also, I'm making the inference using CPU, that for this demo is fine, since we are using a light `sckit-learn`  model.

For large models we need to use heavi parallelism using CUDA for example to take advantage te cores of the GPU.

-----------------


The answers for filter tickets requesting `GET http://localhost:5000/requests?category=technical`.

all the records could need to be paginated to avoid overload the client.

------------------

To consult the DB thinking in large Datasets, I implemented Batch processing in `database.py`, basically we consult the DB in batches.

Extra improvements related to the DB could be:

- Improve the indexes in the DB
- try to sharding the DB by dates or another field.
- The response of the DB can be paginated
- optimize the configuration of the DB:

```
CREATE INDEX CONCURRENTLY {index} ON TABLE USING BRIN (categories);
CREATE INDEX CONCURRENTLY {index} ON TABLE USING GIN (Something);
CREATE UNIQUE INDEX CONCURRENTLY idx_ticket_id ON TABLE (TICKET_id) INCLUDE (master_category, sub_category);

ALTER TABLE products SET (
    autovacuum_vacuum_scale_factor = 0,
    autovacuum_vacuum_threshold = 10000,
    autovacuum_analyze_scale_factor = 0,
    autovacuum_analyze_threshold = 20000
); 

# To implement this we need to make test, so I didn't implement in the code.
```

But this needs to be tested and evaluate carefully.


# More improvements

2. We can implement pagination in the endpoints response and fetching the data in the DB
3. Can be explored compress metadata.
4. The inference worker  can process by batches if is needed.
5. we can implement memoization to cache frequent queries using cachetools for example and cache the S3 connections.
7. In a real project the workers will be in a cluster (like kubernetes or ECS), so apply load balancers.
8. DB Sharding (is complex to implement but can be explored)

and etc.

----------------------

In order to use a large pre-train model, is needed to implement a dataloader to upload the data for the inference in the model:
```
loader = DataLoader(
    dataset,
    batch_size=int(os.getenv("BATCH_SIZE", 64)),  # Aumentar batch size
    num_workers=int(os.getenv("NUM_WORKERS", os.cpu_count() // 2)),  # Usar 50% de los cores
    pin_memory=True,  # Better GPU transfer.
    prefetch_factor=3,
    persistent_workers=True,
    multiprocessing_context='fork' if os.name != 'nt' else 'spawn'
)
```

Use CUDA to execute parallelism using the GPU threads

--------------------

## Alembic Migrations.

It was setUp alembic schema migrations to execute locally.

You can check the alembic folder with the versions of the db.

For now there aren't any change in the versions of the db, because is the initial schema.

The initial setUp for alembic is locally.

For further improvements and taking into account that this is a distributed system, in a real scenario, alembic should be
deployed in a container. Could be an independent container, or fore example in the API container.

## What is missing?

- Complete unit tests.
- (Optional) Deploy Alembic in docker container (could be in a dedicate container or in an existing container with DB access)
- Refactor code, this is a naive implementation.

And probably more things.

## Code Refactor

For scalability of the code and easier maintain, could be beneficial implement and refactor the code structure implementing some patters,
for example follow clean architecture pattern and principles, Isolating the business logic from external resources like API,
message brokers, DBs, Redis, Workers, in general any external infrastructure.


This is a bit complex and tedious to implement, however could be some advantages if is implemented a clean architecture
(we can explore more patterns).

Its simpler write unittest, specially for the business logic. Taking into account that everything is isolated and core business doesn't
depend on  external resources, is simpler write unittest because you don't have to deal with external dependencies. Just test the pure business logic.

Taking into account that in core business, `use_cases` doesn't depend of concrete implementations (depends on `ABS classes`),
change dependencies are simpler. For example, if we want to change `RabbitMQ `for `Kafka`, we only need implement `Kafka` and inject 
the `ABS class` to the `use_case` (remember, use_case depends on interfaces not concrete implementations.) We don't need to change nothing in the logic business.

Or if we want to migrate everything for a serverless, and use `AWS Lambda`, `AWS kinesis`, instead of `Celery` and `RabbitMQ`,
again is just inject the corresponding `ABS classes` and implement them.

And also if we use microservice is easier to scale them.

Again, this is a bit complex to implement, but in some cases could be worth. However, this needs to be discussed because make a migration abd refactored
the code follow clean architectural principles or another patterns (like MVC) could be complex and take time. If the team is small and with limited time,
probably is not the time for this.
