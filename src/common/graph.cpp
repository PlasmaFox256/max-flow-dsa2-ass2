#include "maxflow/graph.hpp"
#include <limits>
#include <stdexcept>

namespace maxflow {
Graph::Graph(std::size_t vertices) : adjacency_(vertices) {
    if (vertices < 2) throw std::invalid_argument("at least two vertices required");
}
void Graph::add_edge(Vertex from, Vertex to, Capacity capacity) {
    if (from >= vertex_count() || to >= vertex_count())
        throw std::invalid_argument("vertex outside graph");
    if (from == to) throw std::invalid_argument("self-loops are excluded");
    if (capacity < 0) throw std::invalid_argument("negative capacity");
    if (capacity > std::numeric_limits<Capacity>::max() - capacity_sum_)
        throw std::overflow_error("sum of capacities exceeds int64 range");
    const EdgeId id = edges_.size();
    edges_.push_back({from, to, capacity});
    edges_.push_back({to, from, 0});
    adjacency_[from].push_back(id);
    adjacency_[to].push_back(reverse(id));
    originals_.push_back({from, to, capacity, id});
    capacity_sum_ += capacity;
}
void Graph::push(EdgeId id, Capacity amount) {
    auto& forward = edges_.at(id);
    if (amount < 0 || amount > forward.residual)
        throw std::invalid_argument("push exceeds residual capacity");
    forward.residual -= amount;
    edges_.at(reverse(id)).residual += amount;
}
void Graph::reset() {
    for (const auto& original : originals_) {
        edges_[original.forward].residual = original.capacity;
        edges_[reverse(original.forward)].residual = 0;
    }
}
}
