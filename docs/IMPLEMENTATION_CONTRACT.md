# Shared implementation contract

## Ownership and workflow

| Area | Owner |
| --- | --- |
| `src/algorithms/edmonds_karp.cpp` | Sam |
| `src/algorithms/push_relabel.cpp` | Dima |
| Shared graph, public interfaces, build, runner, verification | Coordinate together |

Implement inside your own module. Put algorithm-private helpers in an anonymous
namespace, or use separately named private headers. Do not edit the other
algorithm. Agree on shared interface changes before merging. Do not introduce
algorithm-specific behavior into the shared graph.

## Exact signature

```cpp
Capacity edmonds_karp(Graph& graph, Vertex source, Vertex sink);
Capacity push_relabel(Graph& graph, Vertex source, Vertex sink);
```

`Capacity` is `std::int64_t`; `Vertex` and `EdgeId` are `std::size_t`.
The caller supplies valid distinct terminals and a graph with zero flow.
The solver returns the exact maximum-flow value and leaves a feasible maximum
flow in the residual graph. The topology cannot change during a solve.
The source need not be vertex 0, and the sink need not be the last vertex.

No parsing, printing, file output, timers, or global mutable state in a solver.
All algorithm-local initialization and allocation belongs inside the timed call.
Do not reset the graph inside the solver; the caller provides fresh state.

## Shared graph API

- `graph.vertex_count()` gives the number of vertices.
- `graph.outgoing(u)` gives residual edge IDs leaving vertex `u`.
- `graph.edge(id)` gives a read-only `{from, to, residual}` record.
- `Graph::reverse(id)` gives the paired reverse residual edge ID.
- `graph.push(id, amount)` updates both sides of that pair.
- `graph.original_edges()` exposes `{from, to, capacity, forward}` for each
  original directed edge. Its flow is `capacity - graph.edge(forward).residual`.
- `graph.reset()` is for callers/tests between independent solves.

Both algorithms must use this representation and mutation method. Keep local
queues, heights, excess, predecessor arrays, and current-edge pointers in your
own module. Reverse residual edges are usable by both algorithms, even though
those edges were not explicitly present in the input. Parallel and opposite-
direction original edges always own separate pairs.

## Sam: Edmonds–Karp

Replace the placeholder with BFS over edges with positive residual capacity.
Track predecessor **edge IDs**, not only predecessor vertices: parallel edges
make the distinction necessary. Recover a path, determine its bottleneck, push
along every edge, and repeat until the sink is unreachable.

## Dima: push–relabel

Start with FIFO active-vertex processing and current-edge pointers. Heights,
excess, queue membership, and edge cursors are local state. Exclude source and
sink from active-vertex discharge. Update the shared graph through `push`.
Do not stop merely because the sink has received the maximum value: discharge
all internal excess, returning it toward the source when necessary, so the
returned residual graph encodes a feasible flow.

Add global relabeling only after the baseline passes. Preserve the baseline as
a separately selectable variant if it will be compared experimentally; agree
on its public registration before adding it. No heuristic is implemented here.

## Definition of done for each algorithm

1. Replace the placeholder and retain the assigned author credit.
2. Pass your CTest suite in Debug and Release, plus the framework suite.
3. Run the experiment smoke configuration; your rows must be `ok` and verified.
4. Confirm the other implementation's file and the shared interface were not
   changed incidentally.
5. Open a small reviewable change describing the algorithm and checks run.

A skipped suite means unfinished, not verified. Both solvers must pass before
reporting comparative performance. Never use placeholder timings as results.
