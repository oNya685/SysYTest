int main()
{
	int i,j,k,n;
	int flag=0;
	n=153;
	i=n/100;
	j=n%100/10;
	k=n%10;
	if(n==i*i*i+j*j*j+k*k*k)	
		flag=1;
	
	return flag;
}
