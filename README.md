# bhopengraph: A python library to create BloodHound OpenGraphs 

<p align="center">
  A python library to create BloodHound OpenGraphs easily
  <br>
  <img alt="PyPI" src="https://img.shields.io/pypi/v/bhopengraph">
  <img alt="GitHub release (latest by date)" src="https://img.shields.io/github/v/release/p0dalirius/bhopengraph">
  <a href="https://twitter.com/intent/follow?screen_name=podalirius_" title="Follow"><img src="https://img.shields.io/twitter/follow/podalirius_?label=Podalirius&style=social"></a>
  <a href="https://www.youtube.com/c/Podalirius_?sub_confirmation=1" title="Subscribe"><img alt="YouTube Channel Subscribers" src="https://img.shields.io/youtube/channel/subscribers/UCF_x5O7CSfr82AfNVTKOv_A?style=social"></a>
  <img height=21px src="https://img.shields.io/badge/Get bloodhound:-191646"> <a href="https://specterops.io/bloodhound-enterprise/" title="Get BloodHound Enterprise"><img alt="Get BloodHound Enterprise" height=21px src="https://mintlify.s3.us-west-1.amazonaws.com/specterops/assets/enterprise-edition-pill-tag.svg"></a>
  <a href="https://specterops.io/bloodhound-community-edition/" title="Get BloodHound Community"><img alt="Get BloodHound Community" height=21px src="https://mintlify.s3.us-west-1.amazonaws.com/specterops/assets/community-edition-pill-tag.svg"></a>
  <br>
  <br>
  This library also exists in: <a href="https://github.com/TheManticoreProject/gopengraph">Go</a> | <a href="https://github.com/p0dalirius/bhopengraph">Python</a>
</p>

## Features

This module provides Python classes for creating and managing graph structures that are compatible with BloodHound OpenGraph. The classes follow the [BloodHound OpenGraph schema](https://bloodhound.specterops.io/opengraph/schema) and [best practices](https://bloodhound.specterops.io/opengraph/best-practices).

If you don't know about BloodHound OpenGraph yet, a great introduction can be found here: [https://bloodhound.specterops.io/opengraph/best-practices](https://bloodhound.specterops.io/opengraph/best-practices)

The complete documentation of this library can be found here: https://bhopengraph.readthedocs.io/en/latest/ 

## Examples

Here is an example of a Python program using the [bhopengraph](https://github.com/p0dalirius/bhopengraph) python library to model the [Minimal Working JSON](https://bloodhound.specterops.io/opengraph/schema#minimal-working-json) from the OpenGraph Schema documentation:

```py
from bhopengraph.OpenGraph import OpenGraph
from bhopengraph.Node import Node
from bhopengraph.Edge import Edge
from bhopengraph.Properties import Properties

# Create an OpenGraph instance
graph = OpenGraph(source_kind="Base")

# Create nodes
bob_node = Node(
    id="123",
    kinds=["Person", "Base"],
    properties=Properties(
        displayname="bob",
        property="a",
        objectid="123",
        name="BOB"
    )
)

alice_node = Node(
    id="234",
    kinds=["Person", "Base"],
    properties=Properties(
        displayname="alice",
        property="b",
        objectid="234",
        name="ALICE"
    )
)

# Add nodes to graph
graph.add_node(bob_node)
graph.add_node(alice_node)

# Create edge: Bob knows Alice
knows_edge = Edge(
    start_node=alice_node.id,
    end_node=bob_node.id,
    kind="Knows"
)

# Add edge to graph
graph.add_edge(knows_edge)

# Export to file
graph.export_to_file("minimal_example.json")
```

This gives us the following [Minimal Working JSON](https://bloodhound.specterops.io/opengraph/schema#minimal-working-json) as per the documentation:

```json
{
  "graph": {
    "nodes": [
      {
        "id": "123",
        "kinds": [
          "Person",
          "Base"
        ],
        "properties": {
          "displayname": "bob",
          "property": "a",
          "objectid": "123",
          "name": "BOB"
        }
      },
      {
        "id": "234",
        "kinds": [
          "Person",
          "Base"
        ],
        "properties": {
          "displayname": "alice",
          "property": "b",
          "objectid": "234",
          "name": "ALICE"
        }
      }
    ],
    "edges": [
      {
        "kind": "Knows",
        "start": {
          "value": "123",
          "match_by": "id"
        },
        "end": {
          "value": "234",
          "match_by": "id"
        }
      }
    ]
  },
  "metadata": {
    "source_kind": "Base"
  }
}
```

## Custom Node Icons

bhopengraph includes a `BloodHoundClient` that can authenticate to a BloodHound instance and manage custom node icons. Authentication uses HMAC-signed requests with a token ID and token key pair generated in the BloodHound UI.

### Icons JSON format

The icons file mirrors the BloodHound API format. Each entry has a `kindName` and a `config` containing a Font Awesome icon definition:

```json
{
  "custom_nodes": [
    {
      "kindName": "CustomNodeType",
      "config": {
        "icon": {
          "type": "font-awesome",
          "name": "circle",
          "color": "#17A2B8"
        }
      }
    }
  ]
}
```

A generic template is provided in [`icons.json`](icons.json) and a more complete AWS example in [`icons-example.json`](icons-example.json).

### CLI usage

Upload icons directly from the command line:

```bash
python -m bhopengraph upload-icons \
  --url https://your-bloodhound-instance.example.com \
  --token-id <TOKEN_ID> \
  --token-key '<TOKEN_KEY>' \
  --icons-file icons.json
```

Add `--json` for JSON output.

### Python usage

```py
from bhopengraph import BloodHoundClient

client = BloodHoundClient(
    base_url="https://your-bloodhound-instance.example.com",
    token_id="<TOKEN_ID>",
    token_key="<TOKEN_KEY>"
)

# Upload from file (upserts: updates existing, creates new)
results = client.upload_icons_from_file("icons.json")

# Or load and upload separately
icons = BloodHoundClient.load_icons_from_file("icons.json")
results = client.upload_icons(icons)

# Individual CRUD operations
nodes = client.get_custom_nodes()
node = client.get_custom_node("CustomNodeType")
client.create_custom_node("NewType", {"type": "font-awesome", "name": "star", "color": "#FFD700"})
client.update_custom_node("NewType", {"type": "font-awesome", "name": "star", "color": "#FF0000"})
client.delete_custom_node("NewType")
```

## Contributing

Pull requests are welcome. Feel free to open an issue if you want to add other features.

## References

- [BloodHound OpenGraph Best Practices](https://bloodhound.specterops.io/opengraph/best-practices)
- [BloodHound OpenGraph Schema](https://bloodhound.specterops.io/opengraph/schema)
- [BloodHound OpenGraph API](https://bloodhound.specterops.io/opengraph/api)
- [BloodHound OpenGraph Custom Icons](https://bloodhound.specterops.io/opengraph/custom-icons)
