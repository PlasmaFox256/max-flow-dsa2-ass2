#pragma once
#include "maxflow/graph.hpp"
#include <istream>

namespace maxflow {
struct Instance {
    Graph graph;
    Vertex source;
    Vertex sink;
};
// Strict whitespace-separated format: n m source sink, then m lines u v capacity.
// Vertices are zero-based. No comments or trailing tokens.
Instance read_instance(std::istream& input);
}
