#include "maxflow/verify.hpp"
#include <queue>
#include <stdexcept>
#include <vector>

namespace maxflow {
void verify_max_flow(const Graph& graph, Vertex source, Vertex sink, Capacity value) {
    const auto n = graph.vertex_count();
    if (source >= n || sink >= n || source == sink || value < 0)
        throw std::runtime_error("invalid terminals or flow value");
    std::vector<Capacity> balance(n, 0);
    for (const auto& original : graph.original_edges()) {
        const auto remaining = graph.edge(original.forward).residual;
        const auto backward = graph.edge(Graph::reverse(original.forward)).residual;
        if (remaining < 0 || remaining > original.capacity ||
            backward != original.capacity - remaining)
            throw std::runtime_error("invalid residual pair or capacity violation");
        const auto flow = original.capacity - remaining;
        balance[original.from] -= flow;
        balance[original.to] += flow;
    }
    for (Vertex v = 0; v < n; ++v) {
        const Capacity expected = v == source ? -value : (v == sink ? value : 0);
        if (balance[v] != expected) throw std::runtime_error("flow balance violation");
    }
    std::vector<bool> reachable(n, false);
    std::queue<Vertex> queue;
    reachable[source] = true;
    queue.push(source);
    while (!queue.empty()) {
        const auto u = queue.front();
        queue.pop();
        for (const auto id : graph.outgoing(u)) {
            const auto& edge = graph.edge(id);
            if (edge.residual > 0 && !reachable[edge.to]) {
                reachable[edge.to] = true;
                queue.push(edge.to);
            }
        }
    }
    if (reachable[sink]) throw std::runtime_error("augmenting path remains");
    Capacity cut = 0;
    for (const auto& edge : graph.original_edges())
        if (reachable[edge.from] && !reachable[edge.to]) cut += edge.capacity;
    if (cut != value) throw std::runtime_error("flow differs from cut capacity");
}
}
