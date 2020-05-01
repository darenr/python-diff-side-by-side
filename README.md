# python-diff-side-by-side
show file differences in a side by side html output

Example Usage:

```
    file1 = "/tmp/pyspark_1.py"
    file2 = "/tmp/pyspark_2.py"


    print(DiffCode(file1, file2, name=file2).format(syntax_css='vs', print_width=80))

    # in a notebook:
    # display(HTML(DiffCode(file1, file2, name=file2).format(syntax_css='vs', print_width=80)))

```
