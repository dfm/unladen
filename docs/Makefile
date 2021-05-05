default: dirhtml

BUILDDIR = _build

.PHONY: clean
clean:
	rm -rf $(BUILDDIR)/*

.PHONY: dirhtml
dirhtml:
	python -m sphinx.cmd.build -b dirhtml -d $(BUILDDIR)/doctrees . $(BUILDDIR)/dirhtml
