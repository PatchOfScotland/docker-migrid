#!/bin/bash

docker network create --driver overlay --subnet 10.20.0.0/16 --attachable jupyter_service_default