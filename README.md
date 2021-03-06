# Dispatch API
Interact with an approximate model of Australia's National Electricity Market Dispatch Engine (NEMDE) via an API. Users submit NEMDE case files to the API which are posted to a Redis Queue. Workers monitoring the queue take these parameters, formulate and solve an optimisation problem approximating NEMDE, and then post results back to the queue.

This repository is intended to provide a simple interface allowing users to interact with the model. There is no need to set up solvers or dependancies - these are all managed using Docker containers. If you're interested in model development please see [https://github.com/akxen/nemde](https://github.com/akxen/nemde). Learn how to use the API and explore potential use cases at [https://akxen.github.io/dispatch-api-docs](https://akxen.github.io/dispatch-api-docs).


## Configuration steps
1. Clone repository: `git clone --recurse-submodules https://github.com/akxen/dispatch-api`
2. Set up MySQL database environment variables. Rename `mysql/nemde-mysql-template.env` to `mysql/nemde-mysql.env`. Set `MYSQL_PASSWORD` and `MYSQL_ROOT_PASSWORD` environment variables.
3. Set up API environment variables. Rename `api/config/nemde-api-base-template.env` to `api/config/nemde-api-base.env`. Set missing envirnoment variables. Ensure `MYSQL_PASSWORD` is the same as `MYSQL_ROOT_PASSWORD` in `mysql/nemde-mysql.env`.
4. Set up Redis Queue dashboard environment varaibles. Rename `dashboard-template.env` to `dashboard.env`.
5. Set up NEMDE worker environment variables. Rename `nemde-worker/config/nemde-worker-template.env` to `nemde-worker/config/nemde-worker.env`. Use the following settings for missing environment variables:

| Name | Value |
| ---- | ----- |
| REDIS_HOST | nemde_redis |
| REDIS_PORT | 6379 |
| REDIS_DB | 0 |
| REDIS_QUEUE | public | 
6. Run `docker-compose up --build` to run services.
7. See the docs at [https://akxen.github.io/dispatch-api-docs](https://akxen.github.io/dispatch-api-docs) to explore potential use cases.
