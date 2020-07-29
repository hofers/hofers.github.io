#!/usr/bin/env bash

./bin/srcset.sh assets/images

cd assets/images/
../../bin/cwebp-dir.sh
cd class-blog
../../../bin/cwebp-dir.sh