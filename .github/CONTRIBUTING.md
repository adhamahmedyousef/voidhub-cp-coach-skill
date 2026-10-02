# Contributing

Coach Mo combines coaching instructions with small Python helpers. Keep changes
focused, explain the behavior they improve, and include evidence for factual
claims about problems or learning resources.

## Making a change

Start from the current `main` branch and open a pull request describing the
problem, the change and the checks you ran. Update the relevant reference when
coaching behavior changes. Keep `SKILL.md` concise and load supporting guidance
only when needed.

The helpers use Python 3.10 or newer and the standard library. Run the regression
suite from the repository root:

```text
python -B -m unittest discover -s .github/tests -v
```

Add focused tests for changed API or persistence behavior. Preserve existing
learner records and provide a migration when the saved schema changes. Topic
changes should include prerequisites and a clear mastery criterion. Automated
checks verify mechanics; teaching quality also needs session review.

## Reports and examples

Use minimal, reproducible examples. Never commit API keys, personal learner
records or private contest material. Describe resource verification honestly;
checking a video's title is different from reviewing its explanation.

Report vulnerabilities through the [security policy](SECURITY.md). All
participation follows the [code of conduct](CODE_OF_CONDUCT.md).
