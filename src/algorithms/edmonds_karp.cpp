#include "maxflow/solver.hpp"
#include <algorithm>
#include <limits>
#include <vector>

namespace maxflow {
// Primary author: Sam
Capacity edmonds_karp(Graph& graph, Vertex source, Vertex sink) {
    const auto n = graph.vertex_count();
    if (source >= n || sink >= n || source == sink)
        throw std::invalid_argument("invalid Edmonds-Karp terminals");

    const auto unseen = std::numeric_limits<EdgeId>::max();
    std::vector<EdgeId> predecessor(n, unseen);
    std::vector<Vertex> queue;
    queue.reserve(n);
    Capacity flow = 0;

    while (true) {
        std::fill(predecessor.begin(), predecessor.end(), unseen);
        queue.clear();
        queue.push_back(source);

        // Store edge IDs so parallel and reverse residual edges stay distinct.
        for (std::size_t head = 0;
             head < queue.size() && predecessor[sink] == unseen; ++head) {
            for (const auto id : graph.outgoing(queue[head])) {
                const auto& edge = graph.edge(id);
                if (edge.residual <= 0 || edge.to == source ||
                    predecessor[edge.to] != unseen)
                    continue;
                predecessor[edge.to] = id;
                queue.push_back(edge.to);
                if (edge.to == sink) break;
            }
        }
        if (predecessor[sink] == unseen) return flow;

        Capacity bottleneck = std::numeric_limits<Capacity>::max();
        for (auto v = sink; v != source; ) {
            const auto& edge = graph.edge(predecessor[v]);
            bottleneck = std::min(bottleneck, edge.residual);
            v = edge.from;
        }
        for (auto v = sink; v != source; ) {
            const auto id = predecessor[v];
            v = graph.edge(id).from;
            graph.push(id, bottleneck);
        }
        flow += bottleneck;
    }
}
}
