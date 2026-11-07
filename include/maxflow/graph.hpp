#pragma once
#include <cstddef>
#include <cstdint>
#include <vector>

namespace maxflow {
using Vertex = std::size_t;
using EdgeId = std::size_t;
using Capacity = std::int64_t;

struct ResidualEdge {
    Vertex from;
    Vertex to;
    Capacity residual;
};
struct OriginalEdge {
    Vertex from;
    Vertex to;
    Capacity capacity;
    EdgeId forward;
};

// Each original edge owns a separate residual pair, even for antiparallel edges.
// An edge's reverse ID is id ^ 1. Topology is fixed during a solve.
class Graph {
public:
    explicit Graph(std::size_t vertices);
    void add_edge(Vertex from, Vertex to, Capacity capacity);
    void push(EdgeId id, Capacity amount);
    void reset();
    std::size_t vertex_count() const { return adjacency_.size(); }
    const std::vector<EdgeId>& outgoing(Vertex v) const { return adjacency_.at(v); }
    const ResidualEdge& edge(EdgeId id) const { return edges_.at(id); }
    const std::vector<OriginalEdge>& original_edges() const { return originals_; }
    static EdgeId reverse(EdgeId id) { return id ^ EdgeId{1}; }
private:
    std::vector<std::vector<EdgeId>> adjacency_;
    std::vector<ResidualEdge> edges_;
    std::vector<OriginalEdge> originals_;
    Capacity capacity_sum_ = 0;
};
}
