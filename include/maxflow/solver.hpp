#pragma once
#include "maxflow/graph.hpp"
#include <stdexcept>

namespace maxflow {
class NotImplemented : public std::logic_error {
public:
    explicit NotImplemented(const char* name) : std::logic_error(name) {}
};
// Preconditions: valid distinct terminals; graph has zero flow (fresh or reset).
// Postconditions: return exact max-flow value and leave a FEASIBLE maximum flow
// in graph. Preserve topology. No I/O, timers, global state, or graph reset here.
// All algorithm-specific allocation and initialization belongs inside the call.
using Solver = Capacity (*)(Graph&, Vertex source, Vertex sink);
Capacity edmonds_karp(Graph&, Vertex source, Vertex sink);
Capacity push_relabel(Graph&, Vertex source, Vertex sink);
}
