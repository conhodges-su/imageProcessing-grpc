
proto: 
	python3 -m grpc_tools.protoc -I/Users/connor_hodges/SeattleU/cs5200/indiv --python_out=. --grpc_python_out=. /Users/connor_hodges/SeattleU/cs5200/indiv/protobufs/image.proto

mv:
	mv protobufs/image_pb2* .


	python3 -m grpc_tools.protoc\
	 -I/Users/connor_hodges/SeattleU/cs5200/indiv/protobufs/\
	 --python_out=. --grpc_python_out=/Users/connor_hodges/SeattleU/cs5200/indiv\
	 /Users/connor_hodges/SeattleU/cs5200/indiv/protobufs/image.proto