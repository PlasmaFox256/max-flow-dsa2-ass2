#pragma once
#include "maxflow/graph.hpp"

namespace maxflow {
// Throws if capacity constraints, conservation, terminal balance, or the
// max-flow/min-cut certificate fail. Always runs outside the timing interval.
void verify_max_flow(const Graph&, Vertex source, Vertex sink, Capacity value);
}
