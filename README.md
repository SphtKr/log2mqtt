Proxy Sensor MQTT
===

Summary
--- 

A tool that runs as a daemon alongside a proxy server (e.g. e2guardian) and infers activities from the log information
based on defined rules. This is intended to be somewhat like a "Screen Time" tracker based on proxy logs instead of
direct observation of client device activity.

Dependencies
---

* Python 3.10+
* paho-mqtt

Configuration
---

Refer to the included file config_example.yaml

Proxy Log
---

The e2guardian log format is the initial target for this tool, though the intent is to be flexible enough to handle any text
log format. The config file allows the specification of a delimiter for fields, and numerical indexes (zero-based) where
the needed data values can be found. The tool parses new log file lines and extracts information about users, client hosts,
and their request URLs.

Clients
---

Clients in the context of this tool are devices/hosts such as an iPhone or a desktop PC that are configured to use the proxy.
Clients may have multiple identifiers from the log file, and any `aliases` configured for the client will refer to the configured
client, which will always report activity under its own configured `name`.

Users
---
Users may be associated with one or more clients explicitly, or can be inferred directly from the proxy log file _if_ an associated
username appears in the log file itself. If a client is associated with a user in the config file, all activity assigned to that
client will also be assigned to that user. Behavior when the same client is assigned to more than one user is undefined!

Patterns
---
A pattern is a rule or rules that matches a single proxy log entry. The pattern can match:

* the URL via a regular expression
* the hostname in the URL via a simple substring
* the HTTP method by an exact string match
* the user-agent in the logfile via a regular expression

If more than one of these arguments is specified for a single pattern, then all arguments must match for the pattern to be considered
to match. In most places where patterns are used, however, multiple patterns can be specified (with one or multiple arguments) and any
of the specified patterns matching (with all of the pattern's arguments) in that context will satisfy the condition in that context.

Activities
---
TODO