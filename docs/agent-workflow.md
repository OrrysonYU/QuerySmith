# Agent workflow

The intended graph is interpret → select schema → generate SQL → validate SQL → execute → validate result → analyze → render → finalize. 

Every failure is classified before routing. Attempts are capped at three, normalized SQL hashes must be unique,  resource and semantic reties are sepatately bounded, and the absolute request deadline is authoritative.