### A Very Opinionated Release Script (VORS)

Originally written for Rust projects the release.py script manages versioning and branch maintenance of a release.  The project has to conform to the master/develop branch parts of the git-flow style of branch and project management.

A version of the release algorithm, implemented in Scala and integrated with SBT, has been in production at least four years and has managed hundreds of releases for my employer.  

I want the same process for my Rust projects.  But before writing the Rust version I wrote a Python script to prototype some of the details because it's easier to work with Python for prototyping.

It was built and tested against Python 2.7.10 using virtualenv.

To use the script copy the release.py and requirements.txt files to your repo.

```
pip install -r requirements.txt
```

That's it.

In most cases the script can be invoked using the following syntax.

```
./release.py [final xor snapshot]
```

See the beginning of the release.py script for other options.

It's doubtful I will maintain the script once I write the Rust version.

The following is used for testing the script using the --testfinal option.

```toml
[dependencies]
vors = 1.0.0
```
