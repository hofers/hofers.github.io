---
title: KinDAG
link: https://seanhofer.com/kindag
source: Personal Project
date: 2023-05-01
image: kindag
---
[KinDAG](/kindag) is a family tree web app I started working on in mid-2023 and is still in development. It's built using TypeScript and React, and is deployed via [Cloudflare Pages](https://pages.cloudflare.com){% out %}. It relies on a [Neo4j](https://neo4j.com/){% out %} graph database in order to supply the nodes and relationships which make up the graph, the credentials for which are supplied by the user. It includes a searchable and navigable 3D rendering of the entire graph, supports basic biographic information, and allows for querying exact relationships & common ancestors between individuals. 