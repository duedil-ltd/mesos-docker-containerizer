all::	build
clean::	clean-py

DOT := \033[34m●\033[39m
TICK := \033[32m✔\033[39m

clean-py:
	find ./containerizer -name "*.py[co]" -exec rm {} \;
