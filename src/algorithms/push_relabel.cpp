#include "maxflow/solver.hpp"
#include <algorithm>
#include <limits>
#include <queue>
#include <vector>

namespace maxflow {
// Primary author: Dima
Capacity push_relabel(Graph& graph, Vertex source, Vertex sink) {
    const auto n = graph.vertex_count();
    if (source >= n || sink >= n || source == sink)
        throw std::invalid_argument("invalid push-relabel terminals");

    std::vector<std::size_t> height(n, 0);
    std::vector<std::size_t> current(n, 0);
    std::vector<Capacity> excess(n, 0);
    std::vector<bool> queued(n, false);
    std::queue<Vertex> active;

    const auto activate = [&](Vertex v) {
        if (v != source && v != sink && excess[v] > 0 && !queued[v]) {
            active.push(v);
            queued[v] = true;
        }
    };
    const auto push = [&](EdgeId id, Capacity amount) {
        const auto from = graph.edge(id).from;
        const auto to = graph.edge(id).to;
        graph.push(id, amount);
        excess[from] -= amount;
        excess[to] += amount;
        activate(to);
    };

    // Establish a valid preflow. Negative source excess tracks net outflow.
    height[source] = n;
    for (const auto id : graph.outgoing(source)) {
        const auto amount = graph.edge(id).residual;
        if (amount > 0) push(id, amount);
    }

    while (!active.empty()) {
        const auto u = active.front();
        active.pop();
        // Keep u marked queued throughout its discharge. It leaves with zero
        // excess and may be activated again by a later incoming push.
        const auto& outgoing = graph.outgoing(u);
        while (excess[u] > 0) {
            if (current[u] == outgoing.size()) {
                auto lowest = std::numeric_limits<std::size_t>::max();
                for (const auto id : outgoing) {
                    const auto& edge = graph.edge(id);
                    if (edge.residual > 0) lowest = std::min(lowest, height[edge.to]);
                }
                // An active vertex always has a residual route back toward
                // the source, so at least one residual outgoing edge exists.
                if (lowest == std::numeric_limits<std::size_t>::max())
                    throw std::logic_error("active vertex has no residual outgoing edge");
                height[u] = lowest + 1;
                current[u] = 0;
                continue;
            }
            const auto id = outgoing[current[u]];
            const auto& edge = graph.edge(id);
            if (edge.residual > 0 && height[u] == height[edge.to] + 1) {
                push(id, std::min(excess[u], edge.residual));
            } else {
                ++current[u];
            }
        }
        queued[u] = false;
    }
    // All internal excess is discharged, including excess unable to reach t.
    return excess[sink];
}
}
