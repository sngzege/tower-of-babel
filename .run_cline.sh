#!/bin/bash
cd /home/seng/tower-of-babel
export OPENROUTER_API_KEY=$(grep OPENROUTER_API_KEY /home/seng/.hermes/.env | cut -d= -f2)
exec cline -P openrouter -m kimi/k3 --auto-approve true -s "$(cat /home/seng/tower-of-babel/.cline_prompt_phase8.md)"
