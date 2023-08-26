---
title: KinDAG | Personal Project
h1: KinDAG
h2: A Simple Genealogy App
---
{% include modules/image.html image="kindag" title="An example image of KinDAG, a simple Genealogy app" class="blog-img"%}
<h3>What is it?</h3>
[KinDAG](https://kindag.smhh.dev){% out %} is a family tree web app I started working on in mid-2023. It's built using TypeScript and React, and is deployed via [Cloudflare Pages](https://pages.cloudflare.com){% out %}. I decided to make it after I started doing ancestry research and I couldn't find a simple genealogy app that had the full tree visualization, searchability, and relationship querying abilities that I wanted. The name comes from the fact that a family tree is technically not a "tree" at all but is instead a "[directed acyclic graph](https://en.m.wikipedia.org/wiki/Directed_acyclic_graph){% out %}".

<h3>How does it work?</h3>
KinDAG relies on a [Neo4j](https://neo4j.com/){% out %} graph database in order to supply the nodes and relationships which make up the graph. As a result, the very first page you're presented with is a login page asking for Neo4j database credentials. If you don't already have a Neo4j database to use, you can set up your own, either by hosting one locally or online, or via [AuraDB](https://neo4j.com/cloud/platform/aura-graph-database/){% out %} (follow the link, click "Get Started Free", complete the sign-up flow, then click "New Instance" under AuraDB Instances; name and configure your instance). 

Using a graph database as opposed to a relational database allows us to easily query relationships between ancestors' nodes in a way we otherwise couldn't, and it allows to do so without adding redundant data to our database. Each ancestor has personal information stored in their node and a list of unidirectional "is child of" relationships pointing to and from their parents and children, respectively.

{% include modules/image.html image="kindag-graph" title="An example of a KinDAG graph, showing many nodes and their connecting relationships" class="blog-img"%}

After logging into a database with valid credentials, you're met with the rendering of its graph. An empty graph will have no nodes or relationships and will essentially look like a blank screen. A populated graph would look something like the image above (though a different graph will have a different shape). From here, you can control the app using keyboard shortcuts on desktop (e.g. open the side panel by hitting "Space", etc.), the table for which can be viewed by clicking on the ? icon in the bottom right corner, or on mobile by tapping the up arrow the bottom right corner to open the bottom panel and navigating from there.

{% include modules/image.html image="kindag-panel" title="An example of an empty ancestor info panel, rendered to the right of the graph and with space for biographical information like name, birth place, birth and death year, notes, links, and more" class="blog-img"%}

Clicking on any node will navigate to that node and open the panel to the selected ancestor. You can also focus on a specific ancestor by searching for them in the top right of the panel, or by selecting their name from the Parents or Children sections of another ancestor's info panel. The selected ancestor's information can be edited by clicking "Edit Ancestor" under their name.

The panel also includes a Query Relationship section at the bottom which allows you to check the familial connection between two ancestors. It accepts two ancestors as input, with the input box for the first auto-filling to the active panel ancestor, and will note that "[Ancestor A] is not related to [Ancestor B]" or otherwise explain the familial relationships between them (e.g. 2x Great Grandparent, Sibling, Great Aunt/Uncle, 4x Cousin, 7 time(s) removed, etc.) and note their common ancestors where they have them (i.e. for aunts/uncles/cousins). If there is more than one way they are related (i.e. they are cousins through both parents), it will note them all.

New ancestors can be added manually by clicking "Add New Ancestor", at which point the panel turns into a new ancestor form which accepts all the fields available on the info panel's edit form, including all their biographical details as well as any parents or children who already exist in the graph. After submitting a new ancestor, the graph will reload and the new node will be present and navigable. 

New ancestors can also be added via the associated browser extension, which is currently unreleased and under development. The extension can be configured to grab biographical information from the current web page, and provides the user with an extension panel containing parent and children selectors and a submit button, which submits the new ancestor with their biographical info and relationships into the database. More to come on that soon!