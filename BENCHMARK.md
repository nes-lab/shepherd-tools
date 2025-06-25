# Benchmarking

The main culprit that slowdowns start of sheep is pydantic v2

```Shell
sudo python3 -X importtime -c 'from shepherd_core.data_models.task import EmulationTask' 2> importtime.log
#  8.4 s on v2023.8.6, pydantic 1.10
# 13.9 s on v2023.8.7, pydantic 2.2.1, core 2.6.1
# 13.7 s with defer_build=True ⇾ triggers bug?
# 12.8 s on v2024.4.1, pydantic 2.7.0, core 2.18.1
# 10.3 s on v2024.5.1, pydantic 2.7.4, core 2.18.4 - debian 12.5
# 10.4 s on v2024.5.1, pydantic 2.8.0, core 2.20.0
# 12.3 s on v2024.8.2, pydantic 2.8.2, core 2.20.1
# 11.7 s on v2024.8.2, pydantic 2.9.0, core 2.23.2
# 18.7 s on v2024.9.1, pydantic 2.9.2, core 2.23.4 - python 3.13 via uv
# 12.2 s on v2024.11.3, pydantic 2.10.6, core 2.27.2
#  8.9 s on v2024.11.3, pydantic 2.11.0a1, core 2.28.0
#  9.5 s on v2025.2.2, pydantic 2.11.1, core 2.33.0
#  9.5 s on v2025.6.3, pydantic 2.11.7, core 2.33.2 - py 3.11 in venv via uv
```
